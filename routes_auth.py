from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from db import get_db
from models import SaaSUser

router = APIRouter()

@router.post("/login-saas")
def login_saas(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(SaaSUser).filter(SaaSUser.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not check_password_hash(str(user.password_hash), password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    request.session["saas_user_id"] = user.id
    request.session["account_id"] = user.account_id

    request.session.pop("user_id", None)
    request.session.pop("role", None)

    return {"ok": True}
