from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from database.models import Document, Event, Reminder

def create_document(db: Session, **data):
    data["important_dates"] = data.get("important_dates") if isinstance(data.get("important_dates"), str) else json.dumps(data.get("important_dates") or [], ensure_ascii=False)
    obj = Document(**data); db.add(obj); db.commit(); db.refresh(obj); return obj

def get_document(db, document_id): return db.query(Document).filter(Document.id == document_id).first()
def get_event(db, event_id): return db.query(Event).filter(Event.id == event_id).first()

def list_documents(db, *, q=None, document_type=None, due_within_days=None, expiry_year=None, sort_by="created_at", order="desc"):
    query = db.query(Document)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(or_(Document.document_name.ilike(pattern), Document.file_name.ilike(pattern), Document.owner_name.ilike(pattern), Document.reference_number.ilike(pattern), Document.notes.ilike(pattern), Document.extracted_text.ilike(pattern)))
    if document_type and document_type.lower() != "all": query = query.filter(Document.document_type == document_type)
    today = date.today()
    if due_within_days is not None and due_within_days >= 0:
        query = query.filter(Document.expiry_date.isnot(None), Document.expiry_date >= today, Document.expiry_date <= today + timedelta(days=due_within_days))
    if expiry_year: query = query.filter(Document.expiry_date.isnot(None), func.strftime("%Y", Document.expiry_date) == str(expiry_year))
    column = {"created_at": Document.created_at, "expiry_date": Document.expiry_date, "issue_date": Document.issue_date, "document_name": Document.document_name, "document_type": Document.document_type}.get(sort_by, Document.created_at)
    return query.order_by(column.asc() if order.lower() == "asc" else column.desc()).all()

def list_overdue_documents(db, limit=100): return db.query(Document).filter(Document.expiry_date.isnot(None), Document.expiry_date < date.today()).order_by(Document.expiry_date.asc()).limit(limit).all()

def update_document(db, document_id, data):
    obj = get_document(db, document_id)
    if not obj: return None
    if "important_dates" in data and not isinstance(data["important_dates"], str): data["important_dates"] = json.dumps(data["important_dates"] or [], ensure_ascii=False)
    for key, value in data.items():
        if hasattr(obj, key): setattr(obj, key, value)
    db.commit(); db.refresh(obj); return obj

def delete_document(db, document_id, delete_file=True):
    obj = get_document(db, document_id)
    if not obj: return False
    db.query(Reminder).filter(Reminder.source_type == "document", Reminder.source_id == document_id).delete(synchronize_session=False)
    if delete_file and obj.file_path: Path(obj.file_path).unlink(missing_ok=True)
    db.delete(obj); db.commit(); return True

def create_event(db, **data):
    obj = Event(**data); db.add(obj); db.commit(); db.refresh(obj); return obj

def list_events(db, *, q=None, upcoming_days=None, sort_by="event_date", order="asc"):
    query = db.query(Event)
    if q:
        pattern = f"%{q.strip()}%"; query = query.filter(or_(Event.title.ilike(pattern), Event.description.ilike(pattern)))
    if upcoming_days is not None and upcoming_days >= 0: query = query.filter(Event.event_date >= date.today(), Event.event_date <= date.today() + timedelta(days=upcoming_days))
    column = {"event_date": Event.event_date, "title": Event.title, "created_at": Event.created_at}.get(sort_by, Event.event_date)
    return query.order_by(column.asc() if order.lower() == "asc" else column.desc()).all()

def update_event(db, event_id, data):
    obj = get_event(db, event_id)
    if not obj: return None
    for key, value in data.items():
        if hasattr(obj, key): setattr(obj, key, value)
    db.commit(); db.refresh(obj); return obj

def delete_event(db, event_id):
    obj = get_event(db, event_id)
    if not obj: return False
    db.query(Reminder).filter(Reminder.source_type == "event", Reminder.source_id == event_id).delete(synchronize_session=False)
    db.delete(obj); db.commit(); return True

def create_reminder(db, *, source_type, source_id, reminder_date):
    if db.query(Reminder).filter_by(source_type=source_type, source_id=source_id, reminder_date=reminder_date).first(): return None
    obj = Reminder(source_type=source_type, source_id=source_id, reminder_date=reminder_date); db.add(obj); db.commit(); db.refresh(obj); return obj

def delete_unsent_reminders(db, *, source_type, source_id, from_date=None):
    query = db.query(Reminder).filter_by(source_type=source_type, source_id=source_id, sent=False)
    if from_date: query = query.filter(Reminder.reminder_date >= from_date)
    query.delete(synchronize_session=False); db.commit()
def get_due_reminders(db, as_of_date): return db.query(Reminder).filter(Reminder.sent == False, Reminder.reminder_date <= as_of_date).order_by(Reminder.reminder_date.asc()).all()  # noqa: E712
def mark_reminder_sent(db, reminder): reminder.sent = True; db.commit()
def get_recent_reminders(db, limit=10): return db.query(Reminder).order_by(Reminder.id.desc()).limit(limit).all()

def get_dashboard_stats(db):
    today = date.today(); in_30 = today + timedelta(days=30); in_7 = today + timedelta(days=7)
    return {"documents_count": db.query(func.count(Document.id)).scalar() or 0, "events_count": db.query(func.count(Event.id)).scalar() or 0,
            "expiring_30_count": db.query(func.count(Document.id)).filter(Document.expiry_date >= today, Document.expiry_date <= in_30).scalar() or 0,
            "overdue_count": db.query(func.count(Document.id)).filter(Document.expiry_date < today).scalar() or 0,
            "upcoming_events_30_count": db.query(func.count(Event.id)).filter(Event.event_date >= today, Event.event_date <= in_30).scalar() or 0,
            "critical_count": db.query(func.count(Document.id)).filter(Document.expiry_date.isnot(None), or_(Document.expiry_date < today, Document.expiry_date <= in_7)).scalar() or 0}
