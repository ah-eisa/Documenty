from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import repository
from database.db import get_db
from schemas import EventCreate, EventOut, EventUpdate
from services import reminder_service
router = APIRouter(prefix="/api/events", tags=["events"])
@router.post("", response_model=EventOut)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    obj = repository.create_event(db, **payload.model_dump()); reminder_service.sync_event_reminders(db, obj); return obj
@router.get("", response_model=list[EventOut])
def list_events(q: str | None = None, upcoming_days: int | None = None, sort_by: str = "event_date", order: str = "asc", db: Session = Depends(get_db)):
    return repository.list_events(db, q=q, upcoming_days=upcoming_days, sort_by=sort_by, order=order)
@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)):
    obj = repository.get_event(db, event_id)
    if not obj: raise HTTPException(404, "Event not found")
    return obj
@router.put("/{event_id}", response_model=EventOut)
def update_event(event_id: int, payload: EventUpdate, db: Session = Depends(get_db)):
    obj = repository.update_event(db, event_id, payload.model_dump(exclude_unset=True))
    if not obj: raise HTTPException(404, "Event not found")
    reminder_service.sync_event_reminders(db, obj); return obj
@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    if not repository.delete_event(db, event_id): raise HTTPException(404, "Event not found")
    return {"success": True}
