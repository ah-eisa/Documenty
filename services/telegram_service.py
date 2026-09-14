from datetime import date
import httpx
from config import settings

def is_configured(): return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)
def send_message(text):
    if not is_configured(): return False
    try:
        response = httpx.post(f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text[:4000]}, timeout=30)
        return response.is_success
    except Exception: return False
def send_daily_report(text): return send_message(text)
def send_expiry_alert(document):
    if not document or not document.expiry_date: return False
    days = (document.expiry_date - date.today()).days
    return send_message(f"Document expiry alert\n{document.document_name or document.file_name}\nExpiry: {document.expiry_date}\nDays left: {days}")
def send_event_alert(event):
    if not event or not event.event_date: return False
    return send_message(f"Event reminder\n{event.title}\nDate: {event.event_date}")
