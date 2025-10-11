from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func
from db import init_db, get_db
from sqlalchemy.orm import Session
from models import Deposit, Expense, PaidFromEnum
from security import SESSION_SECRET, get_current_user, generate_csrf_token
from seed_data import seed_database
import os

from routers import auth, crew, deposits, expenses, receipts, balances, export as export_router

app = FastAPI(title="Crew Wallet - Bordkasse")

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

init_db()

with next(get_db()) as db:
    seed_database(db)

app.include_router(auth.router)
app.include_router(crew.router)
app.include_router(deposits.router)
app.include_router(expenses.router)
app.include_router(receipts.router)
app.include_router(balances.router)
app.include_router(export_router.router)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    total_deposits = db.query(func.sum(Deposit.amount_eur)).scalar() or 0.0
    
    wallet_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.paid_from == PaidFromEnum.wallet
    ).scalar() or 0.0
    
    private_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.paid_from == PaidFromEnum.private
    ).scalar() or 0.0
    
    total_expenses = wallet_expenses + private_expenses
    wallet_balance = total_deposits - wallet_expenses
    
    top_categories = db.query(
        Expense.category,
        func.sum(Expense.amount_eur).label('total')
    ).group_by(Expense.category).order_by(func.sum(Expense.amount_eur).desc()).limit(5).all()
    
    expense_count = db.query(Expense).count()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "wallet_balance": round(wallet_balance, 2),
        "total_deposits": round(total_deposits, 2),
        "total_expenses": round(total_expenses, 2),
        "wallet_expenses": round(wallet_expenses, 2),
        "private_expenses": round(private_expenses, 2),
        "top_categories": top_categories,
        "expense_count": expense_count,
        "csrf_token": csrf_token
    })
