"""Secure document upload, extraction, persistence, and reprocessing."""

from __future__ import annotations
import logging
import re
import uuid
from datetime import date
from pathlib import Path

from fastapi import UploadFile
from config import settings
from database import repository
from services import ai_service, extraction_service, reminder_service
from services.file_security import sha256, validate_upload, write_secure

logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"}


def process_upload(db, upload_file: UploadFile):
    original_name = Path(upload_file.filename or "file").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type")
    data = upload_file.file.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if len(data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit")
    mime_type = validate_upload(extension, upload_file.content_type, data)
    settings.FILES_DIR.mkdir(parents=True, exist_ok=True)
    internal_name = f"{uuid.uuid4().hex}{extension}"
    saved_path = settings.FILES_DIR / internal_name
    encrypted = write_secure(saved_path, data)
    try:
        return _process_saved_file(db, saved_path, original_name, mime_type, encrypted, sha256(data))
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise


def _process_saved_file(db, path: Path, original_name: str, mime_type: str, encrypted: bool, digest: str):
    from services.file_security import read_secure
    raw_path = path
    if encrypted:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=Path(original_name).suffix, delete=False) as temp:
            temp.write(read_secure(path, True))
            extraction_path = Path(temp.name)
        try:
            extraction = extraction_service.extract_text_detailed(extraction_path)
        finally:
            extraction_path.unlink(missing_ok=True)
    else:
        extraction = extraction_service.extract_text_detailed(raw_path)
    text = str(extraction.get("text") or "")
    info = ai_service.extract_document_info(text, original_name)
    document = repository.create_document(
        db,
        file_name=original_name,
        file_path=str(path),
        document_name=info.get("document_name") or Path(original_name).stem,
        document_type=info.get("document_type") or "Other",
        owner_name=info.get("owner_name"),
        reference_number=info.get("reference_number"),
        issue_date=_as_date(info.get("issue_date")),
        expiry_date=_as_date(info.get("expiry_date")),
        notes=info.get("notes"),
        important_dates=info.get("important_dates", []),
        extracted_text=text,
        mime_type=mime_type,
        is_encrypted=encrypted,
        sha256=digest,
        extraction_status=extraction.get("status", "failed"),
        extraction_error=extraction.get("error"),
        extraction_source=info.get("source") or extraction.get("source"),
        extraction_confidence=info.get("confidence"),
    )
    reminder_service.sync_document_reminders(db, document)
    return document


def reprocess_document(db, document):
    from services.file_security import read_secure
    path = Path(document.file_path).resolve()
    if path.parent != settings.FILES_DIR.resolve() or not path.exists():
        raise ValueError("Document file is missing")
    data = read_secure(path, bool(document.is_encrypted))
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=Path(document.file_name).suffix, delete=False) as temp:
        temp.write(data)
        temp_path = Path(temp.name)
    try:
        extraction = extraction_service.extract_text_detailed(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
    info = ai_service.extract_document_info(str(extraction.get("text") or ""), document.file_name)
    repository.update_document(db, document.id, {
        "document_name": info.get("document_name"), "document_type": info.get("document_type"),
        "owner_name": info.get("owner_name"), "reference_number": info.get("reference_number"),
        "issue_date": _as_date(info.get("issue_date")), "expiry_date": _as_date(info.get("expiry_date")),
        "notes": info.get("notes"), "important_dates": info.get("important_dates", []),
        "extracted_text": extraction.get("text"), "extraction_status": extraction.get("status", "failed"),
        "extraction_error": extraction.get("error"), "extraction_source": info.get("source") or extraction.get("source"),
        "extraction_confidence": info.get("confidence"),
    })
    updated = repository.get_document(db, document.id)
    reminder_service.sync_document_reminders(db, updated)
    return updated


def _as_date(value) -> date | None:
    parsed = ai_service.parse_date_to_iso(value)
    try:
        return date.fromisoformat(parsed) if parsed else None
    except ValueError:
        return None
