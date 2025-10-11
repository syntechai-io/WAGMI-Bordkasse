from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import Expense, ExpenseParticipant, CrewMember, Receipt, PaidFromEnum, SplitModeEnum
from datetime import date
from typing import List, Optional
from pathlib import Path
import uuid

router = APIRouter(prefix="/expenses", tags=["expenses"])
templates = Jinja2Templates(directory="templates")

CATEGORIES = ["Proviant", "Getränke", "Mooring", "Diesel", "Wasser", "Strom", "Gas", "Taxi/Transfer", "Restaurant", "Eintritte", "Sonstiges"]

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024

@router.get("", response_class=HTMLResponse)
async def list_expenses(request: Request, db: Session = Depends(get_db)):
    expenses = db.query(Expense).order_by(Expense.date.desc()).all()
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    
    return templates.TemplateResponse("expenses.html", {
        "request": request,
        "expenses": expenses,
        "crew_members": crew_members,
        "categories": CATEGORIES
    })

@router.post("/new")
async def create_expense(
    request: Request,
    payer_id: int = Form(...),
    expense_date: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    amount_eur: float = Form(...),
    paid_from: str = Form(...),
    split_mode: str = Form(...),
    participant_ids: List[int] = Form([]),
    receipt: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    expense = Expense(
        payer_id=payer_id,
        date=date.fromisoformat(expense_date),
        category=category,
        description=description,
        amount_eur=amount_eur,
        paid_from=PaidFromEnum(paid_from),
        split_mode=SplitModeEnum(split_mode)
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    
    if split_mode == "participants" and participant_ids:
        for pid in participant_ids:
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid))
    elif split_mode == "equal":
        all_members = db.query(CrewMember).all()
        for member in all_members:
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=member.id))
    
    db.commit()
    
    # Handle receipt upload if provided
    receipt_uploaded = False
    if receipt and receipt.filename:
        if receipt.content_type in ALLOWED_CONTENT_TYPES:
            content = await receipt.read()
            if len(content) <= MAX_FILE_SIZE:
                ext_map = {
                    "application/pdf": ".pdf",
                    "image/jpeg": ".jpg",
                    "image/png": ".png"
                }
                ext = ext_map.get(receipt.content_type, ".bin")
                
                filename = str(uuid.uuid4()) + ext
                filepath = Path("uploads") / filename
                
                # Ensure uploads directory exists
                Path("uploads").mkdir(exist_ok=True)
                
                filepath.write_bytes(content)
                
                receipt_record = Receipt(
                    expense_id=expense.id,
                    stored_filename=filename,
                    original_name=receipt.filename or "unknown",
                    content_type=receipt.content_type,
                    size_bytes=len(content)
                )
                db.add(receipt_record)
                db.commit()
                receipt_uploaded = True
    
    # Redirect to detail page if receipt was uploaded, otherwise to list
    if receipt_uploaded:
        return RedirectResponse(url=f"/expenses/{expense.id}", status_code=303)
    else:
        return RedirectResponse(url="/expenses", status_code=303)

@router.get("/{expense_id}", response_class=HTMLResponse)
async def expense_detail(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    return templates.TemplateResponse("expense_detail.html", {
        "request": request,
        "expense": expense
    })

@router.get("/{expense_id}/edit", response_class=HTMLResponse)
async def edit_expense_form(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db)
):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        expenses = db.query(Expense).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Ausgabe nicht gefunden."
        }, status_code=404)
    
    crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
    participant_ids = [p.member_id for p in expense.participants]
    
    return templates.TemplateResponse("expense_edit.html", {
        "request": request,
        "expense": expense,
        "crew_members": crew_members,
        "categories": CATEGORIES,
        "participant_ids": participant_ids
    })

@router.post("/{expense_id}/edit")
async def update_expense(
    request: Request,
    expense_id: int,
    payer_id: int = Form(...),
    expense_date: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    amount_eur: float = Form(...),
    paid_from: str = Form(...),
    split_mode: str = Form(...),
    participant_ids: List[int] = Form([]),
    db: Session = Depends(get_db)
):
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            expenses = db.query(Expense).order_by(Expense.date.desc()).all()
            crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
            return templates.TemplateResponse("expenses.html", {
                "request": request,
                "expenses": expenses,
                "crew_members": crew_members,
                "categories": CATEGORIES,
                "error": "Ausgabe nicht gefunden."
            }, status_code=404)
        
        expense.payer_id = payer_id
        expense.date = date.fromisoformat(expense_date)
        expense.category = category
        expense.description = description
        expense.amount_eur = amount_eur
        expense.paid_from = PaidFromEnum(paid_from)
        expense.split_mode = SplitModeEnum(split_mode)
        
        # Delete existing participants
        db.query(ExpenseParticipant).filter(ExpenseParticipant.expense_id == expense_id).delete()
        
        # Add new participants
        if split_mode == "participants" and participant_ids:
            for pid in participant_ids:
                db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid))
        elif split_mode == "equal":
            all_members = db.query(CrewMember).all()
            for member in all_members:
                db.add(ExpenseParticipant(expense_id=expense.id, member_id=member.id))
        
        db.commit()
        return RedirectResponse(url="/expenses", status_code=303)
    except IntegrityError:
        db.rollback()
        expenses = db.query(Expense).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Ausgabe konnte nicht aktualisiert werden."
        }, status_code=400)

@router.post("/{expense_id}/delete")
async def delete_expense(
    request: Request,
    expense_id: int,
    db: Session = Depends(get_db)
):
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if expense:
            db.delete(expense)
            db.commit()
        return RedirectResponse(url="/expenses", status_code=303)
    except IntegrityError:
        db.rollback()
        expenses = db.query(Expense).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Ausgabe kann nicht gelöscht werden."
        }, status_code=400)
