"""Encrypted local backups with a provider-neutral file interface."""

from __future__ import annotations

import io
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from config import BASE_DIR, settings


def _fernet():
    if not settings.BACKUP_ENCRYPTION_KEY:
        return None
    from cryptography.fernet import Fernet
    return Fernet(settings.BACKUP_ENCRYPTION_KEY.encode())


def _database_path() -> Path:
    prefix = "sqlite:///"
    if not settings.DATABASE_URL.startswith(prefix):
        raise ValueError("Backups currently support SQLite only")
    raw_path = settings.DATABASE_URL[len(prefix):]
    path = Path(raw_path)
    return path if path.is_absolute() else BASE_DIR / raw_path.removeprefix("./")


def _metadata() -> dict:
    safe_keys = {"APP_NAME", "TIMEZONE", "OCR_LANGUAGE", "OPENAI_BASE_URL", "OPENAI_MODEL", "REMINDER_DAYS_DEFAULT", "MAX_UPLOAD_SIZE_MB"}
    import os
    return {key: os.getenv(key, "") for key in safe_keys}


def create_backup() -> Path:
    fernet = _fernet()
    if not fernet:
        raise ValueError("BACKUP_ENCRYPTION_KEY is not configured")
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = settings.BACKUP_DIR / f"documenty-{stamp}.backup"
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        db_copy = root / "app.db"
        source = _database_path()
        if source.exists():
            with sqlite3.connect(source) as src, sqlite3.connect(db_copy) as dst:
                src.backup(dst)
        else:
            sqlite3.connect(db_copy).close()
        shutil.copytree(settings.FILES_DIR, root / "files", dirs_exist_ok=True)
        (root / "metadata.json").write_text(json.dumps(_metadata(), indent=2), encoding="utf-8")
        archive = root / "payload.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in root.rglob("*"):
                if path.is_file() and path != archive:
                    bundle.write(path, path.relative_to(root))
        output.write_bytes(fernet.encrypt(archive.read_bytes()))
    _prune_backups()
    return output


def list_backups() -> list[dict]:
    return [
        {"name": path.name, "size": path.stat().st_size, "modified": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}
        for path in sorted(settings.BACKUP_DIR.glob("*.backup"), reverse=True)
    ]


def _read_archive(path: Path) -> zipfile.ZipFile:
    fernet = _fernet()
    if not fernet:
        raise ValueError("BACKUP_ENCRYPTION_KEY is not configured")
    return zipfile.ZipFile(io.BytesIO(fernet.decrypt(path.read_bytes())))


def _safe_extract(bundle: zipfile.ZipFile, root: Path) -> None:
    for member in bundle.infolist():
        target = (root / member.filename).resolve()
        if target != root.resolve() and root.resolve() not in target.parents:
            raise ValueError("Backup contains an unsafe path")
    bundle.extractall(root)


def verify_backup(path: Path) -> bool:
    try:
        with _read_archive(path) as bundle:
            return {"app.db", "metadata.json"}.issubset(bundle.namelist()) and bundle.testzip() is None
    except Exception:
        return False


def restore_backup(name: str) -> None:
    path = (settings.BACKUP_DIR / Path(name).name).resolve()
    if path.parent != settings.BACKUP_DIR.resolve() or not path.exists():
        raise ValueError("Backup not found")
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        with _read_archive(path) as bundle:
            _safe_extract(bundle, root)
        database = _database_path()
        database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / "app.db", database)
        if (root / "files").exists():
            shutil.copytree(root / "files", settings.FILES_DIR, dirs_exist_ok=True)


def _prune_backups() -> None:
    paths = sorted(settings.BACKUP_DIR.glob("*.backup"), key=lambda item: item.stat().st_mtime, reverse=True)
    for path in paths[settings.BACKUP_RETENTION:]:
        path.unlink(missing_ok=True)
