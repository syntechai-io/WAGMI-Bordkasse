from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, Response
from template_helpers import create_templates
from sqlalchemy.orm import Session, joinedload
from db import get_db
from models import CrewMember, Deposit, Expense
from services.trip import TripService
from settlement import compute_settlement
from routers.balances import calculate_balances
from i18n import get_lang, t as i18n_t
from constants.expense_enums import display_expense_category
import io
from defusedcsv import csv
from typing import Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def sanitize_csv_value(value: Any) -> str:
    """
    Sanitize a value for CSV output to prevent formula injection attacks.
    Prefixes values starting with =, +, -, @, |, % with a single quote.
    """
    if value is None:
        return ""
    
    str_value = str(value)
    # Check if the value starts with potentially dangerous characters
    if str_value and str_value[0] in ('=', '+', '-', '@', '|', '%'):
        return "'" + str_value
    return str_value

router = APIRouter(prefix="/export", tags=["export"])
templates = create_templates()

@router.get("/csv", response_class=HTMLResponse)
async def export_page(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    return templates.TemplateResponse("export.html", {
        "request": request,
        "active_trip": active_trip
    })

@router.get("/download")
async def download_csv(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([])
    writer.writerow(["CREW MEMBERS"])
    writer.writerow(["ID", "Code", "Name", "IBAN/Handle"])
    for member in db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all():
        writer.writerow([
            member.id,
            sanitize_csv_value(member.code),
            sanitize_csv_value(member.name),
            sanitize_csv_value(member.iban_or_handle)
        ])
    
    writer.writerow([])
    writer.writerow(["DEPOSITS"])
    writer.writerow(["ID", "Member Code", "Member Name", "Amount EUR", "Date", "Note"])
    for deposit in db.query(Deposit).options(joinedload(Deposit.member)).filter(Deposit.trip_id == active_trip.id).all():
        writer.writerow([
            deposit.id,
            sanitize_csv_value(deposit.member.code),
            sanitize_csv_value(deposit.member.name),
            sanitize_csv_value(deposit.amount_eur),
            sanitize_csv_value(deposit.date),
            sanitize_csv_value(deposit.note)
        ])
    
    writer.writerow([])
    writer.writerow(["EXPENSES"])
    writer.writerow(["ID", "Payer Code", "Payer Name", "Date", "Category", "Description", "Amount EUR", "Paid From", "Split Mode", "Participants"])
    lang = get_lang(request)
    _t = lambda key, **kw: i18n_t(lang, key, **kw)
    for expense in db.query(Expense).options(
        joinedload(Expense.payer),
        joinedload(Expense.participants).joinedload('member')
    ).filter(Expense.trip_id == active_trip.id).all():
        participants = ", ".join([sanitize_csv_value(p.member.code) for p in expense.participants])
        writer.writerow([
            expense.id,
            sanitize_csv_value(expense.payer.code),
            sanitize_csv_value(expense.payer.name),
            sanitize_csv_value(expense.date),
            sanitize_csv_value(display_expense_category(expense.category, _t)),
            sanitize_csv_value(expense.description),
            sanitize_csv_value(expense.amount_eur),
            sanitize_csv_value(expense.paid_from.value),
            sanitize_csv_value(expense.split_mode.value),
            participants
        ])
    
    # Add settlement transfers
    balances, settlement_net_map = calculate_balances(db, active_trip.id)
    transfers = compute_settlement(settlement_net_map)
    
    writer.writerow([])
    writer.writerow(["SETTLEMENT TRANSFERS / AUSGLEICH"])
    writer.writerow(["From Code", "From Name", "To Code", "To Name", "Amount EUR"])
    
    member_map = {m.code: m for m in db.query(CrewMember).filter(
        CrewMember.trip_id == active_trip.id
    ).all()}
    
    for from_code, to_code, amount in transfers:
        writer.writerow([
            sanitize_csv_value(from_code),
            sanitize_csv_value(member_map[from_code].name),
            sanitize_csv_value(to_code),
            sanitize_csv_value(member_map[to_code].name),
            f"{amount:.2f}"
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crew_wallet_export.csv"}
    )

@router.get("/pdf")
async def download_pdf(request: Request, db: Session = Depends(get_db)):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a5f'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # Section header style
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0077be'),
        spaceAfter=10
    )
    
    # Title
    elements.append(Paragraph("⚓ CrewLog Bordkasse - Export", title_style))
    elements.append(Paragraph(f"Trip: {active_trip.name}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Crew Members
    elements.append(Paragraph("👥 Crew Members", section_style))
    crew_data = [["ID", "Code", "Name", "IBAN/Handle"]]
    for member in db.query(CrewMember).filter(CrewMember.trip_id == active_trip.id).all():
        crew_data.append([
            str(member.id),
            str(member.code),
            str(member.name),
            str(member.iban_or_handle) if member.iban_or_handle is not None else ""
        ])
    
    crew_table = Table(crew_data, colWidths=[0.5*inch, 1*inch, 2*inch, 2.5*inch])
    crew_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0077be')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(crew_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Deposits
    elements.append(Paragraph("💰 Deposits", section_style))
    deposit_data = [["ID", "Member", "Amount EUR", "Date", "Note"]]
    for deposit in db.query(Deposit).options(joinedload(Deposit.member)).filter(Deposit.trip_id == active_trip.id).all():
        deposit_data.append([
            str(deposit.id),
            f"{deposit.member.code} - {deposit.member.name}",
            f"€{deposit.amount_eur:.2f}",
            str(deposit.date),
            str(deposit.note) if deposit.note is not None else ""
        ])
    
    deposit_table = Table(deposit_data, colWidths=[0.5*inch, 2*inch, 1.2*inch, 1.2*inch, 2*inch])
    deposit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ecc71')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(deposit_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Expenses
    elements.append(Paragraph("📊 Expenses", section_style))
    lang_pdf = get_lang(request)
    _t_pdf = lambda key, **kw: i18n_t(lang_pdf, key, **kw)
    expense_data = [["ID", "Payer", "Date", "Category", "Description", "Amount EUR", "From", "Split"]]
    for expense in db.query(Expense).options(joinedload(Expense.payer)).filter(Expense.trip_id == active_trip.id).all():
        desc = str(expense.description)
        expense_data.append([
            str(expense.id),
            str(expense.payer.code),
            str(expense.date),
            display_expense_category(expense.category, _t_pdf),
            desc[:30] + "..." if len(desc) > 30 else desc,
            f"€{expense.amount_eur:.2f}",
            str(expense.paid_from.value),
            str(expense.split_mode.value)
        ])
    
    expense_table = Table(expense_data, colWidths=[0.4*inch, 0.8*inch, 0.9*inch, 1*inch, 1.8*inch, 1*inch, 0.8*inch, 0.8*inch])
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b35')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(expense_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Settlement Transfers
    balances, settlement_net_map = calculate_balances(db, active_trip.id)
    transfers = compute_settlement(settlement_net_map)
    
    elements.append(Paragraph("💸 Settlement Transfers / Ausgleich", section_style))
    
    if transfers:
        settlement_data = [["From Code", "From Name", "To Code", "To Name", "Amount EUR"]]
        
        member_map = {m.code: m for m in db.query(CrewMember).filter(
            CrewMember.trip_id == active_trip.id
        ).all()}
        
        for from_code, to_code, amount in transfers:
            settlement_data.append([
                str(from_code),
                str(member_map[from_code].name),
                str(to_code),
                str(member_map[to_code].name),
                f"€{amount:.2f}"
            ])
        
        settlement_table = Table(settlement_data, colWidths=[0.8*inch, 2*inch, 0.8*inch, 2*inch, 1*inch])
        settlement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(settlement_table)
    else:
        elements.append(Paragraph("All settled! No transfers needed.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=crew_wallet_export.pdf"}
    )

@router.get("/health")
async def health_check():
    return {"status": "ok"}
