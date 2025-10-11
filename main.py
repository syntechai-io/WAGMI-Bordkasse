from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import func
from db import init_db, get_db
from sqlalchemy.orm import Session
from models import Deposit, Expense, PaidFromEnum, Trip
from seed_data import seed_database
from services.trip import TripService
import os

from routers.crew import router as crew_router
from routers.deposits import router as deposits_router
from routers.expenses import router as expenses_router
from routers.receipts import router as receipts_router
from routers.balances import router as balances_router
from routers.export import router as export_router
from routers.auth import router as auth_router
from routers.trips import router as trips_router

app = FastAPI(title="Crew Wallet - Bordkasse")

# Auth middleware to protect all routes (must be added BEFORE SessionMiddleware)
from middleware.auth import AuthMiddleware
app.add_middleware(AuthMiddleware)

# Session middleware for authentication (must be added AFTER AuthMiddleware due to LIFO execution)
session_secret = os.getenv("SESSION_SECRET")
if not session_secret:
    raise RuntimeError("SESSION_SECRET environment variable is required for security!")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

init_db()

with next(get_db()) as db:
    seed_database(db)

app.include_router(auth_router)
app.include_router(trips_router)
app.include_router(crew_router)
app.include_router(deposits_router)
app.include_router(expenses_router)
app.include_router(receipts_router)
app.include_router(balances_router)
app.include_router(export_router)

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_active_trip(db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    trip_id = active_trip.id
    
    total_deposits = db.query(func.sum(Deposit.amount_eur)).filter(
        Deposit.trip_id == trip_id
    ).scalar() or 0.0
    
    wallet_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.trip_id == trip_id,
        Expense.paid_from == PaidFromEnum.wallet
    ).scalar() or 0.0
    
    private_expenses = db.query(func.sum(Expense.amount_eur)).filter(
        Expense.trip_id == trip_id,
        Expense.paid_from == PaidFromEnum.private
    ).scalar() or 0.0
    
    total_expenses = wallet_expenses + private_expenses
    wallet_balance = total_deposits - wallet_expenses
    
    top_categories = db.query(
        Expense.category,
        func.sum(Expense.amount_eur).label('total')
    ).filter(Expense.trip_id == trip_id).group_by(Expense.category).order_by(func.sum(Expense.amount_eur).desc()).limit(5).all()
    
    expense_count = db.query(Expense).filter(Expense.trip_id == trip_id).count()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_trip": active_trip,
        "wallet_balance": round(wallet_balance, 2),
        "total_deposits": round(total_deposits, 2),
        "total_expenses": round(total_expenses, 2),
        "wallet_expenses": round(wallet_expenses, 2),
        "private_expenses": round(private_expenses, 2),
        "top_categories": top_categories,
        "expense_count": expense_count
    })
