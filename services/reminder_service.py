from datetime import date, timedelta
from config import settings
from database import repository

def _days(value):
    values = [int(x.strip()) for x in str(value or "").split(",") if x.strip().isdigit()]
    return sorted(set(values or settings.REMINDER_DAYS_DEFAULT), reverse=True)

def _sync(db, source_type, source_id, event_date, offsets):
    today = date.today(); repository.delete_unsent_reminders(db, source_type=source_type, source_id=source_id, from_date=today)
    if not event_date or event_date < today: return
    for offset in set(offsets) | {0}:
        reminder_date = event_date - timedelta(days=offset)
        if reminder_date >= today: repository.create_reminder(db, source_type=source_type, source_id=source_id, reminder_date=reminder_date)

def sync_document_reminders(db, document): _sync(db, "document", document.id, document.expiry_date, settings.REMINDER_DAYS_DEFAULT)
def sync_event_reminders(db, event): _sync(db, "event", event.id, event.event_date, _days(event.reminder_days))
def sync_all_reminders(db):
    from database.models import Document, Event
    for obj in db.query(Document).all(): sync_document_reminders(db, obj)
    for obj in db.query(Event).all(): sync_event_reminders(db, obj)

def process_due_reminders(db):
    from services import telegram_service
    for reminder in repository.get_due_reminders(db, date.today()):
        if reminder.source_type == "document": obj = repository.get_document(db, reminder.source_id); sent = telegram_service.send_expiry_alert(obj) if obj else True
        elif reminder.source_type == "event": obj = repository.get_event(db, reminder.source_id); sent = telegram_service.send_event_alert(obj) if obj else True
        else: sent = True
        if sent or not telegram_service.is_configured(): repository.mark_reminder_sent(db, reminder)
