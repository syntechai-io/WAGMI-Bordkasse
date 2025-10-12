from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from db import get_db
from models import Expense, ExpenseParticipant, CrewMember, Receipt, PaidFromEnum, SplitModeEnum, Currency
from services.trip import TripService
from services.currency import CurrencyService
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
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
    
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
    amount: float = Form(...),
    currency: str = Form(Currency.EUR.value),
    paid_from: str = Form(...),
    split_mode: str = Form(...),
    participant_ids: List[int] = Form([]),
    participant_percentages: List[float] = Form([]),
    receipt: Optional[UploadFile] = File(None),
    clientTempId: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Check for duplicate using clientTempId (prevents duplicate entries during sync)
    if clientTempId:
        existing_expense = db.query(Expense).filter(
            Expense.client_temp_id == clientTempId
        ).first()
        if existing_expense:
            # Expense already exists, return success
            return RedirectResponse(url="/expenses", status_code=303)
    
    if amount <= 0:
        expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Der Betrag muss positiv sein."
        }, status_code=400)
    
    try:
        currency_enum = Currency(currency)
        amount_eur = CurrencyService.convert_to_eur(amount, currency_enum)
        
        expense = Expense(
            trip_id=active_trip.id,
            client_temp_id=clientTempId,
            payer_id=payer_id,
            date=date.fromisoformat(expense_date),
            category=category,
            description=description,
            amount=amount,
            currency=currency_enum,
            amount_eur=amount_eur,
            paid_from=PaidFromEnum(paid_from),
            split_mode=SplitModeEnum(split_mode)
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
    except (IntegrityError, ValueError):
        db.rollback()
        expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Ausgabe konnte nicht erstellt werden."
        }, status_code=400)
    
    if split_mode == "percentage":
        if not participant_ids:
            db.rollback()
            db.delete(expense)
            db.commit()
            expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
            crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
            return templates.TemplateResponse("expenses.html", {
                "request": request,
                "expenses": expenses,
                "crew_members": crew_members,
                "categories": CATEGORIES,
                "error": "Mindestens ein Teilnehmer muss für Prozent-Aufteilung ausgewählt werden."
            }, status_code=400)
        
        if len(participant_ids) != len(participant_percentages):
            db.rollback()
            db.delete(expense)
            db.commit()
            expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
            crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
            return templates.TemplateResponse("expenses.html", {
                "request": request,
                "expenses": expenses,
                "crew_members": crew_members,
                "categories": CATEGORIES,
                "error": "Anzahl der Teilnehmer und Prozentsätze stimmt nicht überein."
            }, status_code=400)
        
        if any(p <= 0 or p > 100 for p in participant_percentages):
            db.rollback()
            db.delete(expense)
            db.commit()
            expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
            crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
            return templates.TemplateResponse("expenses.html", {
                "request": request,
                "expenses": expenses,
                "crew_members": crew_members,
                "categories": CATEGORIES,
                "error": "Jeder Prozentsatz muss zwischen 0 und 100 liegen."
            }, status_code=400)
        
        total_percentage = sum(participant_percentages)
        if abs(total_percentage - 100.0) > 0.01:
            db.rollback()
            db.delete(expense)
            db.commit()
            expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
            crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
            return templates.TemplateResponse("expenses.html", {
                "request": request,
                "expenses": expenses,
                "crew_members": crew_members,
                "categories": CATEGORIES,
                "error": f"Prozentsätze müssen genau 100% ergeben (aktuell: {total_percentage}%)."
            }, status_code=400)
        
        for pid, percentage in zip(participant_ids, participant_percentages):
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid, percentage=percentage))
    elif split_mode == "participants" and participant_ids:
        percentage_per_participant = 100.0 / len(participant_ids)
        for pid in participant_ids:
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid, percentage=percentage_per_participant))
    elif split_mode == "equal":
        all_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all()
        percentage_per_member = 100.0 / len(all_members) if all_members else 0
        for member in all_members:
            db.add(ExpenseParticipant(expense_id=expense.id, member_id=member.id, percentage=percentage_per_member))
    
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
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.trip_id == active_trip.id
    ).first()
    
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
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.trip_id == active_trip.id
    ).first()
    if not expense:
        expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Ausgabe nicht gefunden."
        }, status_code=404)
    
    crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
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
    amount: float = Form(...),
    currency: str = Form(Currency.EUR.value),
    paid_from: str = Form(...),
    split_mode: str = Form(...),
    participant_ids: List[int] = Form([]),
    participant_percentages: List[float] = Form([]),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    if amount <= 0:
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.trip_id == active_trip.id
        ).first()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        participant_ids = [p.member_id for p in expense.participants] if expense else []
        return templates.TemplateResponse("expense_edit.html", {
            "request": request,
            "expense": expense,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "participant_ids": participant_ids,
            "error": "Der Betrag muss positiv sein."
        }, status_code=400)
    
    try:
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.trip_id == active_trip.id
        ).first()
        if not expense:
            expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
            crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
            return templates.TemplateResponse("expenses.html", {
                "request": request,
                "expenses": expenses,
                "crew_members": crew_members,
                "categories": CATEGORIES,
                "error": "Ausgabe nicht gefunden."
            }, status_code=404)
        
        currency_enum = Currency(currency)
        amount_eur = CurrencyService.convert_to_eur(amount, currency_enum)
        
        expense.payer_id = payer_id  # type: ignore[assignment]
        expense.date = date.fromisoformat(expense_date)  # type: ignore[assignment]
        expense.category = category  # type: ignore[assignment]
        expense.description = description  # type: ignore[assignment]
        expense.amount = amount  # type: ignore[assignment]
        expense.currency = currency_enum  # type: ignore[assignment]
        expense.amount_eur = amount_eur  # type: ignore[assignment]
        expense.paid_from = PaidFromEnum(paid_from)  # type: ignore[assignment]
        expense.split_mode = SplitModeEnum(split_mode)  # type: ignore[assignment]
        
        db.query(ExpenseParticipant).filter(ExpenseParticipant.expense_id == expense_id).delete()
        
        if split_mode == "percentage":
            if not participant_ids:
                db.rollback()
                crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
                participant_ids_display = [p.member_id for p in expense.participants]
                return templates.TemplateResponse("expense_edit.html", {
                    "request": request,
                    "expense": expense,
                    "crew_members": crew_members,
                    "categories": CATEGORIES,
                    "participant_ids": participant_ids_display,
                    "error": "Mindestens ein Teilnehmer muss für Prozent-Aufteilung ausgewählt werden."
                }, status_code=400)
            
            if len(participant_ids) != len(participant_percentages):
                db.rollback()
                crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
                participant_ids_display = [p.member_id for p in expense.participants]
                return templates.TemplateResponse("expense_edit.html", {
                    "request": request,
                    "expense": expense,
                    "crew_members": crew_members,
                    "categories": CATEGORIES,
                    "participant_ids": participant_ids_display,
                    "error": "Anzahl der Teilnehmer und Prozentsätze stimmt nicht überein."
                }, status_code=400)
            
            if any(p <= 0 or p > 100 for p in participant_percentages):
                db.rollback()
                crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
                participant_ids_display = [p.member_id for p in expense.participants]
                return templates.TemplateResponse("expense_edit.html", {
                    "request": request,
                    "expense": expense,
                    "crew_members": crew_members,
                    "categories": CATEGORIES,
                    "participant_ids": participant_ids_display,
                    "error": "Jeder Prozentsatz muss zwischen 0 und 100 liegen."
                }, status_code=400)
            
            total_percentage = sum(participant_percentages)
            if abs(total_percentage - 100.0) > 0.01:
                db.rollback()
                crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
                participant_ids_display = [p.member_id for p in expense.participants]
                return templates.TemplateResponse("expense_edit.html", {
                    "request": request,
                    "expense": expense,
                    "crew_members": crew_members,
                    "categories": CATEGORIES,
                    "participant_ids": participant_ids_display,
                    "error": f"Prozentsätze müssen genau 100% ergeben (aktuell: {total_percentage}%)."
                }, status_code=400)
            
            for pid, percentage in zip(participant_ids, participant_percentages):
                db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid, percentage=percentage))
        elif split_mode == "participants" and participant_ids:
            percentage_per_participant = 100.0 / len(participant_ids)
            for pid in participant_ids:
                db.add(ExpenseParticipant(expense_id=expense.id, member_id=pid, percentage=percentage_per_participant))
        elif split_mode == "equal":
            all_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all()
            percentage_per_member = 100.0 / len(all_members) if all_members else 0
            for member in all_members:
                db.add(ExpenseParticipant(expense_id=expense.id, member_id=member.id, percentage=percentage_per_member))
        
        db.commit()
        return RedirectResponse(url="/expenses", status_code=303)
    except (IntegrityError, ValueError):
        db.rollback()
        expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
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
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    try:
        expense = db.query(Expense).filter(
            Expense.id == expense_id,
            Expense.trip_id == active_trip.id
        ).first()
        if expense:
            db.delete(expense)
            db.commit()
        return RedirectResponse(url="/expenses", status_code=303)
    except IntegrityError:
        db.rollback()
        expenses = db.query(Expense).filter(Expense.trip_id == active_trip.id).order_by(Expense.date.desc()).all()
        crew_members = db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).order_by(CrewMember.code).all()
        return templates.TemplateResponse("expenses.html", {
            "request": request,
            "expenses": expenses,
            "crew_members": crew_members,
            "categories": CATEGORIES,
            "error": "Ausgabe kann nicht gelöscht werden."
        }, status_code=400)
