"""Maintenance & warranty log: service records for the boat, scoped to the
SaaS account. Viewing is open to any account member (crew should be able to
see what's due); creating/editing/deleting and attachments are owner-only,
matching the boat-profile edit permission in routes_boat.py."""
from __future__ import annotations

import io
import logging
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session, joinedload

from auth_saas import get_active_account_id, get_current_saas_user
from db import get_db
from maintenance_pdf_template import render_maintenance_pdf
from models import Currency, MaintenanceAttachment, MaintenanceRecord
from services import maintenance as MaintenanceService
from services.boat import compute_boat_stats, get_or_create_boat_profile
from template_helpers import create_templates

router = APIRouter(prefix="/admin/maintenance", tags=["maintenance"])
templates = create_templates()
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOADS_DIR = Path("uploads").resolve()
_EXT_MAP = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def _parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_float(value: str) -> Optional[float]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_currency(value: str) -> Optional[Currency]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return Currency(value)
    except ValueError:
        return None


def _require_owner(request: Request, db: Session):
    """Returns the current SaaSUser, raising 403 if they're not the account
    owner. Callers must already have confirmed an active account_id."""
    user = get_current_saas_user(request, db)
    if not user.is_owner:
        raise HTTPException(status_code=403, detail="Only the account owner can edit the maintenance log")
    return user


@router.get("", response_class=HTMLResponse)
async def list_maintenance(request: Request, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)

    user = get_current_saas_user(request, db)
    boat_profile = get_or_create_boat_profile(db, account_id)
    boat_stats = compute_boat_stats(db, account_id)
    records = MaintenanceService.list_records_for_account(db, account_id)

    rows = [
        {"record": r, "due": MaintenanceService.due_status(r, boat_stats)}
        for r in records
    ]
    due_soon_count = sum(1 for row in rows if row["due"] == "due_soon")
    overdue_count = sum(1 for row in rows if row["due"] == "overdue")

    return templates.TemplateResponse("maintenance_log.html", {
        "request": request,
        "boat_profile": boat_profile,
        "boat_stats": boat_stats,
        "rows": rows,
        "is_owner": user.is_owner,
        "due_soon_count": due_soon_count,
        "overdue_count": overdue_count,
        "categories": MaintenanceService.CATEGORIES,
        "statuses": MaintenanceService.STATUSES,
        "currencies": [c.value for c in Currency],
        "today": date.today().isoformat(),
    })


@router.post("/create")
async def create_maintenance_record(
    request: Request,
    title: str = Form(...),
    category: str = Form("service"),
    status: str = Form("resolved"),
    performed_at: str = Form(""),
    engine_hours_at: str = Form(""),
    nm_at: str = Form(""),
    vendor: str = Form(""),
    cost_amount: str = Form(""),
    cost_currency: str = Form(""),
    notes: str = Form(""),
    next_due_date: str = Form(""),
    next_due_engine_hours: str = Form(""),
    next_due_nm: str = Form(""),
    db: Session = Depends(get_db),
):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    _require_owner(request, db)

    if not title or not title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    if category not in MaintenanceService.CATEGORIES:
        category = "service"
    if status not in MaintenanceService.STATUSES:
        status = "resolved"

    MaintenanceService.create_record(
        db,
        account_id=account_id,
        title=title.strip(),
        category=category,
        status=status,
        performed_at=_parse_date(performed_at) or date.today(),
        engine_hours_at=_parse_float(engine_hours_at),
        nm_at=_parse_float(nm_at),
        vendor=vendor.strip() or None,
        cost_amount=_parse_float(cost_amount),
        cost_currency=_parse_currency(cost_currency),
        notes=notes.strip() or None,
        next_due_date=_parse_date(next_due_date),
        next_due_engine_hours=_parse_float(next_due_engine_hours),
        next_due_nm=_parse_float(next_due_nm),
    )
    request.session["success"] = "Eintrag angelegt."
    return RedirectResponse(url="/admin/maintenance", status_code=303)


@router.post("/{record_id}/edit")
async def update_maintenance_record(
    request: Request,
    record_id: int,
    title: str = Form(""),
    category: str = Form(""),
    status: str = Form(""),
    performed_at: str = Form(""),
    engine_hours_at: str = Form(""),
    nm_at: str = Form(""),
    vendor: str = Form(""),
    cost_amount: str = Form(""),
    cost_currency: str = Form(""),
    notes: str = Form(""),
    next_due_date: str = Form(""),
    next_due_engine_hours: str = Form(""),
    next_due_nm: str = Form(""),
    db: Session = Depends(get_db),
):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    _require_owner(request, db)

    updated = MaintenanceService.update_record(
        db,
        account_id=account_id,
        record_id=record_id,
        title=title.strip() or None,
        category=category if category in MaintenanceService.CATEGORIES else None,
        status=status if status in MaintenanceService.STATUSES else None,
        performed_at=_parse_date(performed_at),
        engine_hours_at=_parse_float(engine_hours_at),
        nm_at=_parse_float(nm_at),
        vendor=vendor.strip() or None,
        cost_amount=_parse_float(cost_amount),
        cost_currency=_parse_currency(cost_currency),
        notes=notes.strip() or None,
        next_due_date=_parse_date(next_due_date),
        next_due_engine_hours=_parse_float(next_due_engine_hours),
        next_due_nm=_parse_float(next_due_nm),
    )
    request.session["success" if updated else "error"] = (
        "Eintrag aktualisiert." if updated else "Eintrag nicht gefunden."
    )
    return RedirectResponse(url="/admin/maintenance", status_code=303)


@router.post("/{record_id}/delete")
async def delete_maintenance_record(request: Request, record_id: int, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    _require_owner(request, db)

    record = MaintenanceService.get_record_or_none(db, account_id, record_id)
    if record:
        for attachment in list(record.attachments):
            _delete_attachment_file(attachment.stored_filename)
        MaintenanceService.delete_record(db, account_id, record_id)
        request.session["success"] = "Eintrag gelöscht."
    else:
        request.session["error"] = "Eintrag nicht gefunden."

    return RedirectResponse(url="/admin/maintenance", status_code=303)


def _delete_attachment_file(stored_filename: str) -> None:
    filepath = (UPLOADS_DIR / stored_filename).resolve()
    if filepath.is_relative_to(UPLOADS_DIR) and filepath.exists():
        try:
            filepath.unlink()
        except OSError as e:
            logger.warning(f"Failed to remove maintenance attachment file {stored_filename}: {e}")


@router.post("/{record_id}/attachments")
async def upload_maintenance_attachment(
    request: Request,
    record_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    _require_owner(request, db)

    record = MaintenanceService.get_record_or_none(db, account_id, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF, JPG, and PNG files are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    ext = _EXT_MAP.get(file.content_type, ".bin")
    filename = str(uuid.uuid4()) + ext
    filepath = UPLOADS_DIR / filename

    try:
        UPLOADS_DIR.mkdir(exist_ok=True)
        filepath.write_bytes(content)
    except OSError as e:
        logger.error(f"Failed to write maintenance attachment file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    attachment = MaintenanceAttachment(
        record_id=record_id,
        stored_filename=filename,
        original_name=file.filename or "unknown",
        content_type=file.content_type,
        size_bytes=len(content),
    )
    db.add(attachment)
    db.commit()

    return RedirectResponse(url="/admin/maintenance", status_code=303)


def _get_attachment_for_account(db: Session, account_id: int, attachment_id: int) -> MaintenanceAttachment:
    """Account-scoped lookup — unlike routers/receipts.py's stored-filename
    lookup, this checks the owning record's account_id so one account can
    never view or download another account's maintenance documents."""
    attachment = (
        db.query(MaintenanceAttachment)
        .options(joinedload(MaintenanceAttachment.record))
        .filter(MaintenanceAttachment.id == attachment_id)
        .first()
    )
    if not attachment or attachment.record.account_id != account_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment


@router.get("/attachments/{attachment_id}")
async def download_maintenance_attachment(request: Request, attachment_id: int, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    get_current_saas_user(request, db)  # any account member may view

    attachment = _get_attachment_for_account(db, account_id, attachment_id)
    filepath = (UPLOADS_DIR / attachment.stored_filename).resolve()

    if not filepath.is_relative_to(UPLOADS_DIR):
        logger.warning(f"Path traversal attempt detected: {attachment.stored_filename}")
        raise HTTPException(status_code=403, detail="Access denied")
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found")

    return Response(
        content=filepath.read_bytes(),
        media_type=attachment.content_type,
        headers={"Content-Disposition": f'inline; filename="{attachment.original_name}"'},
    )


@router.post("/attachments/{attachment_id}/delete")
async def delete_maintenance_attachment(request: Request, attachment_id: int, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    _require_owner(request, db)

    attachment = _get_attachment_for_account(db, account_id, attachment_id)
    _delete_attachment_file(attachment.stored_filename)
    db.delete(attachment)
    db.commit()

    return RedirectResponse(url="/admin/maintenance", status_code=303)


@router.get("/export.pdf")
async def export_maintenance_pdf(request: Request, db: Session = Depends(get_db)):
    account_id = get_active_account_id(request)
    if not account_id:
        return RedirectResponse(url="/trips/", status_code=303)
    get_current_saas_user(request, db)  # any account member may export

    boat_profile = get_or_create_boat_profile(db, account_id)
    boat_stats = compute_boat_stats(db, account_id)
    records = MaintenanceService.list_records_for_account(db, account_id)

    pdf_buffer = io.BytesIO()
    try:
        render_maintenance_pdf(
            records=records,
            boat_name=boat_profile.boat_name,
            boat_stats=boat_stats,
            outfile=pdf_buffer,
            meta={"title": f"Wartungslog {boat_profile.boat_name}", "creator": "WAGMI Bordkasse"},
        )
        pdf_buffer.seek(0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"wartungslog_{boat_profile.boat_name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
