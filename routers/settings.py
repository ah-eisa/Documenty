import re
from fastapi import APIRouter, HTTPException
from config import settings, update_env_file
from schemas import SettingsUpdate
from services.telegram_service import send_message
router = APIRouter(prefix="/api/settings", tags=["settings"])
@router.get("")
def get_settings():
    return {"OPENAI_API_KEY": settings.OPENAI_API_KEY, "OPENAI_BASE_URL": settings.OPENAI_BASE_URL, "OPENAI_MODEL": settings.OPENAI_MODEL, "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN, "TELEGRAM_CHAT_ID": settings.TELEGRAM_CHAT_ID, "REMINDER_DAYS_DEFAULT": ",".join(map(str, settings.REMINDER_DAYS_DEFAULT)), "TIMEZONE": settings.TIMEZONE, "API_BASE_URL": settings.API_BASE_URL}
@router.put("")
def update_settings(payload: SettingsUpdate):
    data = {k: str(v or "") for k, v in payload.model_dump(exclude_unset=True).items()}
    if "REMINDER_DAYS_DEFAULT" in data and not re.fullmatch(r"[0-9,\s]*", data["REMINDER_DAYS_DEFAULT"]): raise HTTPException(400, "Reminder days must be comma-separated numbers")
    update_env_file(data); return {"success": True, "message": "Settings saved."}
@router.post("/test-telegram")
def test_telegram():
    if not send_message("Test message from Personal Operations Copilot"): raise HTTPException(502, "Telegram is not configured or unavailable")
    return {"success": True}
