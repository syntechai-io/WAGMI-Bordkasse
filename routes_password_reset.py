import os
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from db import get_db
from models import SaaSUser, PasswordResetToken, AuditLog
from token_utils import generate_reset_token, hash_token, verify_token_hash
from resend_mailer import send_password_reset
from limiter_config import limiter
from i18n import get_lang

logger = logging.getLogger(__name__)

router = APIRouter()

APP_BASE_URL = os.getenv("APP_BASE_URL", "")
TOKEN_EXPIRY_MINUTES = 60


MAX_RESETS_PER_EMAIL_PER_HOUR = 5


def _get_templates():
    from template_helpers import create_templates
    return create_templates()


@router.get("/forgot-password")
async def forgot_password_form(request: Request):
    lang = get_lang(request)
    templates = _get_templates()
    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "sent": False,
    })


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    lang = get_lang(request)
    templates = _get_templates()

    email_lower = email.strip().lower()

    user = db.query(SaaSUser).filter(SaaSUser.email == email_lower).first()

    if user:
        recent_count = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.created_at > datetime.utcnow() - timedelta(hours=1),
            )
            .count()
        )

        if recent_count < MAX_RESETS_PER_EMAIL_PER_HOUR:
            raw_token = generate_reset_token()
            token_hash_val = hash_token(raw_token)

            client_ip = request.client.host if request.client else None
            ua = request.headers.get("user-agent", "")[:500]

            reset_record = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash_val,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
                request_ip=client_ip,
                user_agent=ua,
            )
            db.add(reset_record)

            db.add(AuditLog(
                user_id=user.id,
                action="PASSWORD_RESET_REQUEST",
                entity_type="saas_user",
                entity_id=user.id,
                details=f"Password reset requested for {email_lower}",
                ip_address=client_ip,
            ))

            db.commit()

            base = APP_BASE_URL.rstrip("/") or str(request.base_url).rstrip("/")
            reset_url = f"{base}/reset-password?token={raw_token}"

            send_password_reset(email_lower, reset_url, lang)

    return templates.TemplateResponse("forgot_password.html", {
        "request": request,
        "sent": True,
    })


@router.get("/reset-password")
async def reset_password_form(request: Request, token: str = "", db: Session = Depends(get_db)):
    lang = get_lang(request)
    templates = _get_templates()

    if not token:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": False,
            "token": "",
            "error_key": "reset.invalid_token",
        })

    token_hash_val = hash_token(token)
    reset_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash_val)
        .first()
    )

    if not reset_record or reset_record.used_at is not None:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": False,
            "token": "",
            "error_key": "reset.invalid_token",
        })

    if reset_record.expires_at < datetime.utcnow():
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": False,
            "token": "",
            "error_key": "reset.token_expired",
        })

    return templates.TemplateResponse("reset_password.html", {
        "request": request,
        "valid": True,
        "token": token,
        "error_key": "",
    })


@router.post("/reset-password")
@limiter.limit("10/hour")
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    lang = get_lang(request)
    templates = _get_templates()

    if password != password_confirm:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": True,
            "token": token,
            "error_key": "reset.passwords_mismatch",
        })

    if len(password) < 8:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": True,
            "token": token,
            "error_key": "reset.password_too_short",
        })

    token_hash_val = hash_token(token)
    reset_record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash_val)
        .first()
    )

    if not reset_record or reset_record.used_at is not None:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": False,
            "token": "",
            "error_key": "reset.invalid_token",
        })

    if reset_record.expires_at < datetime.utcnow():
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": False,
            "token": "",
            "error_key": "reset.token_expired",
        })

    user = db.query(SaaSUser).filter(SaaSUser.id == reset_record.user_id).first()
    if not user:
        return templates.TemplateResponse("reset_password.html", {
            "request": request,
            "valid": False,
            "token": "",
            "error_key": "reset.invalid_token",
        })

    user.password_hash = generate_password_hash(password)

    reset_record.used_at = datetime.utcnow()

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.id != reset_record.id,
    ).update({"used_at": datetime.utcnow()}, synchronize_session=False)

    client_ip = request.client.host if request.client else None
    db.add(AuditLog(
        user_id=user.id,
        action="PASSWORD_RESET_SUCCESS",
        entity_type="saas_user",
        entity_id=user.id,
        details="Password successfully reset",
        ip_address=client_ip,
    ))

    db.commit()

    return RedirectResponse(url="/login?reset=success", status_code=303)
