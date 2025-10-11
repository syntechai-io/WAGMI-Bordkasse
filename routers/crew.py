from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db import get_db
from models import CrewMember
from security import require_admin, generate_csrf_token, require_csrf

router = APIRouter(prefix="/crew", tags=["crew"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
async def list_crew(request: Request, db: Session = Depends(get_db), user = Depends(require_admin)):
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("crew_list.html", {
        "request": request,
        "crew_members": crew_members,
        "csrf_token": csrf_token
    })

@router.get("/new", response_class=HTMLResponse)
async def new_crew_form(request: Request, user = Depends(require_admin)):
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("crew_form.html", {
        "request": request,
        "member": None,
        "csrf_token": csrf_token
    })

@router.post("/new")
async def create_crew(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    iban_or_handle: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    require_csrf(request, csrf_token)
    member = CrewMember(code=code, name=name, iban_or_handle=iban_or_handle or None)
    db.add(member)
    db.commit()
    return RedirectResponse(url="/crew", status_code=303)

@router.get("/{member_id}/edit", response_class=HTMLResponse)
async def edit_crew_form(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse("crew_form.html", {
        "request": request,
        "member": member,
        "csrf_token": csrf_token
    })

@router.post("/{member_id}/edit")
async def update_crew(
    request: Request,
    member_id: int,
    code: str = Form(...),
    name: str = Form(...),
    iban_or_handle: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    require_csrf(request, csrf_token)
    member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
    member.code = code
    member.name = name
    member.iban_or_handle = iban_or_handle or None
    db.commit()
    return RedirectResponse(url="/crew", status_code=303)

@router.post("/{member_id}/delete")
async def delete_crew(
    request: Request,
    member_id: int,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    require_csrf(request, csrf_token)
    member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
    db.delete(member)
    db.commit()
    return RedirectResponse(url="/crew", status_code=303)
