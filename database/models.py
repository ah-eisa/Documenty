from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, Index, Integer, String, Text, UniqueConstraint
from database.db import Base

def utcnow(): return datetime.now(timezone.utc)

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_expiry_date", "expiry_date"),)
    id = Column(Integer, primary_key=True, index=True); file_name = Column(String(500), nullable=False)
    document_name = Column(String(500)); file_path = Column(String(1000), nullable=False); document_type = Column(String(100), default="Other")
    owner_name = Column(String(300)); reference_number = Column(String(300)); issue_date = Column(Date); expiry_date = Column(Date)
    notes = Column(Text); important_dates = Column(Text, default="[]"); extracted_text = Column(Text); created_at = Column(DateTime, default=utcnow)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True); title = Column(String(500), nullable=False); description = Column(Text)
    event_date = Column(Date, nullable=False); reminder_days = Column(String(200), default="7,3,1"); created_at = Column(DateTime, default=utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("source_type", "source_id", "reminder_date", name="uq_reminder_source_date"),)
    id = Column(Integer, primary_key=True, index=True); source_type = Column(String(50), nullable=False); source_id = Column(Integer, nullable=False)
    reminder_date = Column(Date, nullable=False); sent = Column(Boolean, default=False, nullable=False); created_at = Column(DateTime, default=utcnow)
