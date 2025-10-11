from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import CrewMember

router = APIRouter(prefix="/crew", tags=["crew"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
async def list_crew(request: Request, db: Session = Depends(get_db)):
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    return templates.TemplateResponse("crew_list.html", {
        "request": request,
        "crew_members": crew_members
    })

@router.get("/new", response_class=HTMLResponse)
async def new_crew_form(request: Request):
    return templates.TemplateResponse("crew_form.html", {
        "request": request,
        "member": None
    })

@router.post("/new")
async def create_crew(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    iban_or_handle: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        member = CrewMember(code=code, name=name, iban_or_handle=iban_or_handle or None)
        db.add(member)
        db.commit()
        return RedirectResponse(url="/crew", status_code=303)
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": None,
            "error": f"Der Code '{code}' existiert bereits. Bitte wählen Sie einen anderen Code."
        }, status_code=400)

@router.get("/{member_id}/edit", response_class=HTMLResponse)
async def edit_crew_form(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db)
):
    member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
    return templates.TemplateResponse("crew_form.html", {
        "request": request,
        "member": member
    })

@router.post("/{member_id}/edit")
async def update_crew(
    request: Request,
    member_id: int,
    code: str = Form(...),
    name: str = Form(...),
    iban_or_handle: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
        member.code = code
        member.name = name
        member.iban_or_handle = iban_or_handle or None
        db.commit()
        return RedirectResponse(url="/crew", status_code=303)
    except IntegrityError:
        db.rollback()
        member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
        return templates.TemplateResponse("crew_form.html", {
            "request": request,
            "member": member,
            "error": f"Der Code '{code}' wird bereits verwendet. Bitte wählen Sie einen anderen Code."
        }, status_code=400)

@router.post("/{member_id}/delete")
async def delete_crew(
    request: Request,
    member_id: int,
    db: Session = Depends(get_db)
):
    member = db.query(CrewMember).filter(CrewMember.id == member_id).first()
    
    if not member:
        return RedirectResponse(url="/crew", status_code=303)
    
    # Check if member has deposits or expenses
    has_deposits = len(member.deposits) > 0
    has_expenses = len(member.paid_expenses) > 0
    
    if has_deposits or has_expenses:
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        error_msg = f"'{member.name}' kann nicht gelöscht werden, da "
        if has_deposits and has_expenses:
            error_msg += "Einzahlungen und Ausgaben existieren."
        elif has_deposits:
            error_msg += "Einzahlungen existieren."
        else:
            error_msg += "Ausgaben existieren."
        error_msg += " Bitte löschen Sie zuerst alle verknüpften Einträge."
        
        return templates.TemplateResponse("crew_list.html", {
            "request": request,
            "crew_members": crew_members,
            "error": error_msg
        }, status_code=400)
    
    try:
        db.delete(member)
        db.commit()
        return RedirectResponse(url="/crew", status_code=303)
    except IntegrityError:
        db.rollback()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("crew_list.html", {
            "request": request,
            "crew_members": crew_members,
            "error": f"'{member.name}' kann nicht gelöscht werden. Bitte löschen Sie zuerst alle verknüpften Einträge."
        }, status_code=400)
