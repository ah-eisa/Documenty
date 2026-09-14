from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from database import repository
from database.db import get_db
from schemas import DocumentOut, DocumentUpdate
from services import document_service, reminder_service
router = APIRouter(prefix="/api/documents", tags=["documents"])
@router.post("/upload", response_model=DocumentOut)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try: return document_service.process_upload(db, file)
    except ValueError as exc: raise HTTPException(400, str(exc))
    except Exception as exc: raise HTTPException(500, f"Failed to process document: {exc}")
@router.get("", response_model=list[DocumentOut])
def list_documents(q: str | None = None, document_type: str | None = None, due_within_days: int | None = Query(None, ge=0), expiry_year: int | None = None, sort_by: str = "created_at", order: str = "desc", db: Session = Depends(get_db)):
    return repository.list_documents(db, q=q, document_type=document_type, due_within_days=due_within_days, expiry_year=expiry_year, sort_by=sort_by, order=order)
@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    obj = repository.get_document(db, document_id)
    if not obj: raise HTTPException(404, "Document not found")
    return obj
@router.put("/{document_id}", response_model=DocumentOut)
def update_document(document_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)):
    obj = repository.update_document(db, document_id, payload.model_dump(exclude_unset=True))
    if not obj: raise HTTPException(404, "Document not found")
    reminder_service.sync_document_reminders(db, obj); return obj
@router.delete("/{document_id}")
def delete_document(document_id: int, delete_file: bool = True, db: Session = Depends(get_db)):
    if not repository.delete_document(db, document_id, delete_file): raise HTTPException(404, "Document not found")
    return {"success": True}
