from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session
from database import repository
from database.db import get_db
from schemas import DocumentOut, DocumentUpdate
from services import document_service, reminder_service
from services.security import current_session
from services.file_security import read_secure
from pathlib import Path
from config import settings
router = APIRouter(prefix="/api/documents", tags=["documents"], dependencies=[Depends(current_session)])
@router.post("/upload", response_model=DocumentOut)
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try: return document_service.process_upload(db, file)
    except ValueError as exc: raise HTTPException(400, str(exc))
    except Exception: raise HTTPException(500, "Failed to process document")
@router.get("", response_model=list[DocumentOut])
def list_documents(q: str | None = None, document_type: str | None = None, due_within_days: int | None = Query(None, ge=0), expiry_year: int | None = None, sort_by: str = "created_at", order: str = "desc", db: Session = Depends(get_db)):
    return repository.list_documents(db, q=q, document_type=document_type, due_within_days=due_within_days, expiry_year=expiry_year, sort_by=sort_by, order=order)
@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    obj = repository.get_document(db, document_id)
    if not obj: raise HTTPException(404, "Document not found")
    return obj


@router.get("/{document_id}/download")
def download_document(document_id: int, db: Session = Depends(get_db)):
    obj = repository.get_document(db, document_id)
    if not obj:
        raise HTTPException(404, "Document not found")
    path = Path(obj.file_path).resolve()
    if path.parent != settings.FILES_DIR.resolve() or not path.exists():
        raise HTTPException(404, "Document file not found")
    try:
        content = read_secure(path, bool(obj.is_encrypted))
    except ValueError:
        raise HTTPException(503, "Document encryption key is unavailable")
    return Response(content=content, media_type=obj.mime_type or "application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{Path(obj.file_name).name}"'})


@router.post("/{document_id}/reprocess", response_model=DocumentOut)
def reprocess_document(document_id: int, db: Session = Depends(get_db)):
    obj = repository.get_document(db, document_id)
    if not obj:
        raise HTTPException(404, "Document not found")
    try:
        return document_service.reprocess_document(db, obj)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
@router.put("/{document_id}", response_model=DocumentOut)
def update_document(document_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)):
    obj = repository.update_document(db, document_id, payload.model_dump(exclude_unset=True))
    if not obj: raise HTTPException(404, "Document not found")
    reminder_service.sync_document_reminders(db, obj); return obj
@router.delete("/{document_id}")
def delete_document(document_id: int, delete_file: bool = True, db: Session = Depends(get_db)):
    if not repository.delete_document(db, document_id, delete_file): raise HTTPException(404, "Document not found")
    return {"success": True}
