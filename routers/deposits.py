from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import Deposit, CrewMember
from datetime import date

router = APIRouter(prefix="/deposits", tags=["deposits"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
async def list_deposits(request: Request, db: Session = Depends(get_db)):
    deposits = db.query(Deposit).order_by(Deposit.date.desc()).all()
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    
    return templates.TemplateResponse("deposits.html", {
        "request": request,
        "deposits": deposits,
        "crew_members": crew_members
    })

@router.post("/new")
async def create_deposit(
    request: Request,
    member_id: int = Form(...),
    amount_eur: float = Form(...),
    deposit_date: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db)
):
    deposit = Deposit(
        member_id=member_id,
        amount_eur=amount_eur,
        date=date.fromisoformat(deposit_date),
        note=note or None
    )
    db.add(deposit)
    db.commit()
    return RedirectResponse(url="/deposits", status_code=303)

@router.get("/{deposit_id}/edit", response_class=HTMLResponse)
async def edit_deposit_form(
    request: Request,
    deposit_id: int,
    db: Session = Depends(get_db)
):
    deposit = db.query(Deposit).filter(Deposit.id == deposit_id).first()
    if not deposit:
        deposits = db.query(Deposit).order_by(Deposit.date.desc()).all()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("deposits.html", {
            "request": request,
            "deposits": deposits,
            "crew_members": crew_members,
            "error": "Einzahlung nicht gefunden."
        }, status_code=404)
    
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    
    return templates.TemplateResponse("deposit_edit.html", {
        "request": request,
        "deposit": deposit,
        "crew_members": crew_members
    })

@router.post("/{deposit_id}/edit")
async def update_deposit(
    request: Request,
    deposit_id: int,
    member_id: int = Form(...),
    amount_eur: float = Form(...),
    deposit_date: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        deposit = db.query(Deposit).filter(Deposit.id == deposit_id).first()
        if not deposit:
            deposits = db.query(Deposit).order_by(Deposit.date.desc()).all()
            crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
            return templates.TemplateResponse("deposits.html", {
                "request": request,
                "deposits": deposits,
                "crew_members": crew_members,
                "error": "Einzahlung nicht gefunden."
            }, status_code=404)
        
        deposit.member_id = member_id
        deposit.amount_eur = amount_eur
        deposit.date = date.fromisoformat(deposit_date)
        deposit.note = note or None
        db.commit()
        return RedirectResponse(url="/deposits", status_code=303)
    except IntegrityError:
        db.rollback()
        deposits = db.query(Deposit).order_by(Deposit.date.desc()).all()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("deposits.html", {
            "request": request,
            "deposits": deposits,
            "crew_members": crew_members,
            "error": "Einzahlung konnte nicht aktualisiert werden."
        }, status_code=400)

@router.post("/{deposit_id}/delete")
async def delete_deposit(
    request: Request,
    deposit_id: int,
    db: Session = Depends(get_db)
):
    try:
        deposit = db.query(Deposit).filter(Deposit.id == deposit_id).first()
        if deposit:
            db.delete(deposit)
            db.commit()
        return RedirectResponse(url="/deposits", status_code=303)
    except IntegrityError:
        db.rollback()
        deposits = db.query(Deposit).order_by(Deposit.date.desc()).all()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("deposits.html", {
            "request": request,
            "deposits": deposits,
            "crew_members": crew_members,
            "error": "Einzahlung kann nicht gelöscht werden."
        }, status_code=400)
