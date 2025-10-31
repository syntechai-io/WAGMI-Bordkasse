from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi_csrf_jinja.jinja_processor import csrf_token_processor
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
from db import get_db
from models import ExpenseTemplate, PaidFromEnum, SplitModeEnum, Currency

router = APIRouter(prefix="/templates", tags=["templates"])
templates = Jinja2Templates(
    directory="templates",
    context_processors=[csrf_token_processor("csrftoken", "x-csrftoken")]
)

@router.get("", response_class=HTMLResponse)
async def list_templates(request: Request, db: Session = Depends(get_db)):
    expense_templates = db.query(ExpenseTemplate).order_by(ExpenseTemplate.name).all()
    return templates.TemplateResponse("templates.html", {
        "request": request,
        "expense_templates": expense_templates
    })

@router.get("/new", response_class=HTMLResponse)
async def new_template_form(request: Request):
    # Global admin-only check (templates are global, not trip-specific)
    if not request.session.get("is_global_admin"):
        raise HTTPException(status_code=403, detail="Nur der Admin kann Vorlagen erstellen")
    
    return templates.TemplateResponse("template_form.html", {
        "request": request,
        "template": None,
        "paid_from_options": [p.value for p in PaidFromEnum],
        "split_mode_options": [s.value for s in SplitModeEnum],
        "currency_options": [c.value for c in Currency]
    })

@router.post("/new")
async def create_template(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    default_amount: Optional[str] = Form(None),
    currency: str = Form(Currency.EUR.value),
    paid_from: str = Form(PaidFromEnum.wallet.value),
    split_mode: str = Form(SplitModeEnum.equal.value),
    db: Session = Depends(get_db)
):
    # Global admin-only check (templates are global, not trip-specific)
    if not request.session.get("is_global_admin"):
        raise HTTPException(status_code=403, detail="Nur der Admin kann Vorlagen erstellen")
    
    # Convert default_amount: empty string or None -> None, otherwise convert to float
    amount_value = None
    if default_amount and default_amount.strip():
        try:
            amount_value = float(default_amount)
            if amount_value <= 0:
                amount_value = None
        except ValueError:
            amount_value = None
    
    template = ExpenseTemplate(
        name=name,
        category=category,
        default_amount=amount_value,
        currency=Currency(currency),
        paid_from=PaidFromEnum(paid_from),
        split_mode=SplitModeEnum(split_mode)
    )
    db.add(template)
    db.commit()
    return RedirectResponse(url="/templates", status_code=303)

@router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_form(request: Request, template_id: int, db: Session = Depends(get_db)):
    # Global admin-only check (templates are global, not trip-specific)
    if not request.session.get("is_global_admin"):
        raise HTTPException(status_code=403, detail="Nur der Admin kann Vorlagen bearbeiten")
    
    template = db.query(ExpenseTemplate).filter(ExpenseTemplate.id == template_id).first()
    if not template:
        return RedirectResponse(url="/templates", status_code=303)
    
    return templates.TemplateResponse("template_form.html", {
        "request": request,
        "template": template,
        "paid_from_options": [p.value for p in PaidFromEnum],
        "split_mode_options": [s.value for s in SplitModeEnum],
        "currency_options": [c.value for c in Currency]
    })

@router.post("/{template_id}/edit")
async def update_template(
    request: Request,
    template_id: int,
    name: str = Form(...),
    category: str = Form(...),
    default_amount: Optional[str] = Form(None),
    currency: str = Form(Currency.EUR.value),
    paid_from: str = Form(PaidFromEnum.wallet.value),
    split_mode: str = Form(SplitModeEnum.equal.value),
    db: Session = Depends(get_db)
):
    # Global admin-only check (templates are global, not trip-specific)
    if not request.session.get("is_global_admin"):
        raise HTTPException(status_code=403, detail="Nur der Admin kann Vorlagen bearbeiten")
    
    template = db.query(ExpenseTemplate).filter(ExpenseTemplate.id == template_id).first()
    if not template:
        return RedirectResponse(url="/templates", status_code=303)
    
    # Convert default_amount: empty string or None -> None, otherwise convert to float
    amount_value = None
    if default_amount and default_amount.strip():
        try:
            amount_value = float(default_amount)
            if amount_value <= 0:
                amount_value = None
        except ValueError:
            amount_value = None
    
    template.name = name
    template.category = category
    template.default_amount = amount_value
    template.currency = Currency(currency)
    template.paid_from = PaidFromEnum(paid_from)
    template.split_mode = SplitModeEnum(split_mode)
    db.commit()
    return RedirectResponse(url="/templates", status_code=303)

@router.post("/{template_id}/delete")
async def delete_template(request: Request, template_id: int, db: Session = Depends(get_db)):
    # Global admin-only check (templates are global, not trip-specific)
    if not request.session.get("is_global_admin"):
        raise HTTPException(status_code=403, detail="Nur der Admin kann Vorlagen löschen")
    
    template = db.query(ExpenseTemplate).filter(ExpenseTemplate.id == template_id).first()
    if template:
        db.delete(template)
        db.commit()
    return RedirectResponse(url="/templates", status_code=303)
