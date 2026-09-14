from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from config import ensure_dirs, settings
from database import repository
from database.db import SessionLocal, get_db, init_db
from routers import documents, events, search, settings as settings_router
from scheduler.jobs import create_scheduler
from services import reminder_service
@asynccontextmanager
async def lifespan(app):
    ensure_dirs(); init_db(); db = SessionLocal()
    try: reminder_service.sync_all_reminders(db)
    finally: db.close()
    scheduler = create_scheduler(); scheduler.start()
    try: yield
    finally: scheduler.shutdown(wait=False)
app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(documents.router); app.include_router(events.router); app.include_router(search.router); app.include_router(settings_router.router)
@app.get("/")
def root(): return {"name": settings.APP_NAME, "status": "running", "docs": "/docs"}
@app.get("/health")
def health(): return {"status": "ok"}
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    alerts = []
    for reminder in repository.get_recent_reminders(db):
        obj = repository.get_document(db, reminder.source_id) if reminder.source_type == "document" else repository.get_event(db, reminder.source_id)
        alerts.append({"id": reminder.id, "source_type": reminder.source_type, "source_id": reminder.source_id, "reminder_date": reminder.reminder_date, "sent": reminder.sent, "title": (getattr(obj, "document_name", None) or getattr(obj, "file_name", None) or getattr(obj, "title", None) or "Deleted")})
    return {**repository.get_dashboard_stats(db), "latest_alerts": alerts}
