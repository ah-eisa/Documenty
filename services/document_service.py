from __future__ import annotations
import re, shutil
from datetime import date, datetime
from pathlib import Path
from fastapi import UploadFile
from config import settings
from database import repository
from services import ai_service, extraction_service, reminder_service
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"}

def process_upload(db, upload_file: UploadFile):
    original = Path(upload_file.filename or "file").name; extension = Path(original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS: raise ValueError("Unsupported file type. Supported: PDF, DOCX, XLSX, JPG, PNG.")
    settings.FILES_DIR.mkdir(parents=True, exist_ok=True); stem = re.sub(r"[^\w\u0600-\u06ff.-]", "_", Path(original).stem)[:80]
    path = settings.FILES_DIR / f"{stem}-{datetime.now():%Y%m%d-%H%M%S}{extension}"
    with path.open("wb") as buffer: shutil.copyfileobj(upload_file.file, buffer)
    text = extraction_service.extract_text(path); info = ai_service.extract_document_info(text, original)
    def as_date(value):
        parsed = ai_service.parse_date_to_iso(value)
        try: return date.fromisoformat(parsed) if parsed else None
        except ValueError: return None
    document = repository.create_document(db, file_name=original, file_path=str(path), document_name=info["document_name"], document_type=info["document_type"], owner_name=info.get("owner_name"), reference_number=info.get("reference_number"), issue_date=as_date(info.get("issue_date")), expiry_date=as_date(info.get("expiry_date")), notes=info.get("notes") or ("No text extracted" if not text else None), important_dates=info.get("important_dates", []), extracted_text=text)
    reminder_service.sync_document_reminders(db, document); return document
