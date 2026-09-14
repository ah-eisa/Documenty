"""Upload validation and transparent optional encryption."""

from __future__ import annotations

import hashlib
from pathlib import Path

from config import settings

ALLOWED_MIME = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}


def detect_mime(data: bytes, supplied: str | None) -> str:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"PK\x03\x04"):
        return supplied if supplied in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"} else "application/zip"
    return supplied or "application/octet-stream"


def validate_upload(extension: str, supplied_mime: str | None, data: bytes) -> str:
    extension = extension.lower()
    if extension not in ALLOWED_MIME:
        raise ValueError("Unsupported file type")
    if not data:
        raise ValueError("Uploaded file is empty")
    mime = detect_mime(data[:4096], supplied_mime)
    if mime not in ALLOWED_MIME[extension]:
        raise ValueError("File type and content do not match")
    if extension == ".pdf" and b"%%EOF" not in data[-1024 * 1024:]:
        raise ValueError("Malformed PDF file")
    return mime


def encryption_enabled() -> bool:
    return bool(settings.ENCRYPTION_KEY)


def _fernet():
    if not settings.ENCRYPTION_KEY:
        return None
    from cryptography.fernet import Fernet
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_bytes(data: bytes) -> bytes:
    fernet = _fernet()
    return fernet.encrypt(data) if fernet else data


def decrypt_bytes(data: bytes, encrypted: bool) -> bytes:
    if not encrypted:
        return data
    fernet = _fernet()
    if not fernet:
        raise ValueError("Document encryption key is not configured")
    return fernet.decrypt(data)


def write_secure(path: Path, data: bytes) -> bool:
    encrypted = encryption_enabled()
    path.write_bytes(encrypt_bytes(data))
    return encrypted


def read_secure(path: Path, encrypted: bool) -> bytes:
    return decrypt_bytes(path.read_bytes(), encrypted)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
