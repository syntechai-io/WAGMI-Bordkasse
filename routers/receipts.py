from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from template_helpers import create_templates
from sqlalchemy.orm import Session
from db import get_db
from models import Receipt, Expense
from services.trip import TripService
from pathlib import Path
import uuid
import logging

router = APIRouter(prefix="/receipts", tags=["receipts"])
templates = create_templates()

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOADS_DIR = Path("uploads").resolve()

@router.post("/expenses/{expense_id}/upload")
async def upload_receipt(
    request: Request,
    expense_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    active_trip = TripService.get_selected_trip(request, db)
    if not active_trip:
        return RedirectResponse(url="/trips", status_code=303)

    expense = db.query(Expense).filter(
        Expense.id == expense_id, Expense.trip_id == active_trip.id
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only PDF, JPG, and PNG files are allowed")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    ext_map = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png"
    }
    ext = ext_map.get(file.content_type, ".bin")
    
    filename = str(uuid.uuid4()) + ext
    filepath = UPLOADS_DIR / filename
    
    try:
        UPLOADS_DIR.mkdir(exist_ok=True)
        filepath.write_bytes(content)
    except (OSError, IOError) as e:
        logger.error(f"Failed to write receipt file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")
    
    receipt = Receipt(
        expense_id=expense_id,
        stored_filename=filename,
        original_name=file.filename or "unknown",
        content_type=file.content_type,
        size_bytes=len(content)
    )
    db.add(receipt)
    db.commit()
    
    return RedirectResponse(url=f"/expenses/{expense_id}", status_code=303)

@router.get("/{receipt_id}", response_class=HTMLResponse)
async def view_receipt(
    request: Request,
    receipt_id: str,
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(Receipt.stored_filename == receipt_id).first()
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    filepath = (UPLOADS_DIR / receipt.stored_filename).resolve()
    
    if not filepath.is_relative_to(UPLOADS_DIR):
        logger.warning(f"Path traversal attempt detected: {receipt_id}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Receipt file not found")
    
    return templates.TemplateResponse("receipt_view.html", {
        "request": request,
        "filename": receipt.stored_filename,
        "original_name": receipt.original_name,
        "content_type": receipt.content_type,
        "expense_id": receipt.expense_id
    })

@router.get("/download/{receipt_id}")
async def download_receipt(
    receipt_id: str,
    db: Session = Depends(get_db)
):
    receipt = db.query(Receipt).filter(Receipt.stored_filename == receipt_id).first()
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    filepath = (UPLOADS_DIR / receipt.stored_filename).resolve()
    
    if not filepath.is_relative_to(UPLOADS_DIR):
        logger.warning(f"Path traversal attempt detected: {receipt_id}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Receipt file not found")
    
    return FileResponse(
        path=str(filepath),
        media_type=str(receipt.content_type),
        filename=str(receipt.original_name)
    )
