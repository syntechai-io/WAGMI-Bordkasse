from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import User
from limiter_config import limiter
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from services.auth import TripAuthService

router = APIRouter()
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

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
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process login with rate limiting (5 attempts per minute per IP)"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not user.check_password(password):
        request.session["login_error"] = "Ungültiger Benutzername oder Passwort"
        return RedirectResponse(url="/login", status_code=303)
    
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    is_global_admin = TripAuthService.is_global_admin(user.id, db)
    request.session["is_global_admin"] = is_global_admin
    
    user_trips = TripAuthService.get_user_trips(user.id, db)
    if user_trips:
        default_trip = user_trips[0]
        TripAuthService.update_session_for_trip(request, user.id, default_trip["trip_id"], db)
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    """Process logout"""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    """Display change password page for logged-in users"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    
    success = request.query_params.get("success")
    error = request.session.get("password_error")
    if error:
        request.session.pop("password_error")
    
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "success": success == "true",
        "error": error
    })

@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Process password change for logged-in user"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    
    # Validate new password
    if len(new_password) < 6:
        request.session["password_error"] = "Neues Passwort muss mindestens 6 Zeichen lang sein."
        return RedirectResponse(url="/change-password", status_code=303)
    
    if new_password != confirm_password:
        request.session["password_error"] = "Neues Passwort und Bestätigung stimmen nicht überein."
        return RedirectResponse(url="/change-password", status_code=303)
    
    # Get current user
    user = db.query(User).filter(User.id == request.session["user_id"]).first()
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Verify current password
    if not user.check_password(current_password):
        request.session["password_error"] = "Aktuelles Passwort ist falsch."
        return RedirectResponse(url="/change-password", status_code=303)
    
    # Update password
    user.set_password(new_password)
    db.commit()
    
    return RedirectResponse(url="/change-password?success=true", status_code=303)

@router.get("/help", response_class=HTMLResponse)
async def help_page(request: Request):
    """Display help/guide page for crew"""
    return templates.TemplateResponse("help.html", {
        "request": request
    })
