from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from security import ADMIN_USER, ADMIN_PASSWORD, create_session_token, generate_csrf_token, require_csrf

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("login.html", {"request": request, "csrf_token": csrf_token})

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...)
):
    require_csrf(request, csrf_token)
    
    if username == ADMIN_USER and password == ADMIN_PASSWORD:
        token = create_session_token(username)
        request.session["user_token"] = token
        return RedirectResponse(url="/", status_code=303)
    
    new_csrf = generate_csrf_token()
    request.session["csrf_token"] = new_csrf
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "error": "Invalid credentials", "csrf_token": new_csrf},
        status_code=401
    )

@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form(...)):
    require_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
