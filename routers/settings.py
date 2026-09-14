import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from config import settings, update_env_file
from schemas import SettingsUpdate
from services.telegram_service import send_message
from services.security import current_session
from services import backup_service
router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(current_session)])
@router.get("")
def get_settings():
    def mask(value: str) -> str:
        return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else ("********" if value else "")
    return {"OPENAI_API_KEY": mask(settings.OPENAI_API_KEY), "OPENAI_BASE_URL": settings.OPENAI_BASE_URL, "OPENAI_MODEL": settings.OPENAI_MODEL, "TELEGRAM_BOT_TOKEN": mask(settings.TELEGRAM_BOT_TOKEN), "TELEGRAM_CHAT_ID": mask(settings.TELEGRAM_CHAT_ID), "REMINDER_DAYS_DEFAULT": ",".join(map(str, settings.REMINDER_DAYS_DEFAULT)), "TIMEZONE": settings.TIMEZONE, "API_BASE_URL": settings.API_BASE_URL, "MAX_UPLOAD_SIZE_MB": settings.MAX_UPLOAD_SIZE_MB, "backup_count": len(backup_service.list_backups())}
@router.put("")
def update_settings(payload: SettingsUpdate):
    data = {k: str(v) for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    for secret_key in ("OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
           if data.get(secret_key) in {"", "********"} or "..." in data.get(secret_key, ""):
            data.pop(secret_key, None)
    if "REMINDER_DAYS_DEFAULT" in data and not re.fullmatch(r"[0-9,\s]*", data["REMINDER_DAYS_DEFAULT"]): raise HTTPException(400, "Reminder days must be comma-separated numbers")
    update_env_file(data); return {"success": True, "message": "Settings saved."}
@router.post("/test-telegram")
def test_telegram():
    if not send_message("Test message from Personal Operations Copilot"): raise HTTPException(502, "Telegram is not configured or unavailable")
    return {"success": True}


@router.post("/backup")
def create_backup():
    try:
        path = backup_service.create_backup()
        return {"name": path.name, "backups": backup_service.list_backups()}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/backups")
def list_backups():
    return {"backups": backup_service.list_backups()}


@router.post("/backups/{name}/verify")
def verify_backup(name: str):
    path = (settings.BACKUP_DIR / Path(name).name).resolve()
    if not backup_service.verify_backup(path):
        raise HTTPException(400, "Backup integrity verification failed")
    return {"valid": True}


@router.post("/backups/{name}/restore")
def restore_backup(name: str):
    try:
        backup_service.restore_backup(name)
        return {"success": True, "message": "Backup restored. Restart the backend."}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
