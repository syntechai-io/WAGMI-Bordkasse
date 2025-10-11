from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from db import get_db
from models import Receipt, Expense
from security import require_admin
from pathlib import Path
import uuid

router = APIRouter(prefix="/receipts", tags=["receipts"])

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_FILE_SIZE = 10 * 1024 * 1024

@router.post("/expenses/{expense_id}/upload")
async def upload_receipt(
    expense_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
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
    filepath = Path("uploads") / filename
    
    filepath.write_bytes(content)
    
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

@router.get("/{receipt_id}")
async def get_receipt(
    receipt_id: str,
    db: Session = Depends(get_db),
    user = Depends(require_admin)
):
    filepath = Path("uploads") / receipt_id
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    receipt = db.query(Receipt).filter(Receipt.stored_filename == receipt_id).first()
    
    return FileResponse(
        path=filepath,
        media_type=receipt.content_type if receipt else "application/octet-stream",
        filename=receipt.original_name if receipt else receipt_id
    )
