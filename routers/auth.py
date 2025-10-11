from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    error = request.session.get("login_error")
    if error:
        request.session.pop("login_error")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not user.check_password(password):
        request.session["login_error"] = "Ungültiger Benutzername oder Passwort"
        return RedirectResponse(url="/login", status_code=303)
    
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role.value
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    """Process logout"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
