from __future__ import annotations
from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; file_name: str; document_name: str | None = None; document_type: str | None = None
    owner_name: str | None = None; reference_number: str | None = None; issue_date: date | None = None
    expiry_date: date | None = None; notes: str | None = None; important_dates: str | None = None; created_at: datetime
    mime_type: str | None = None; is_encrypted: bool = False; extraction_status: str = "pending"
    extraction_error: str | None = None; extraction_source: str | None = None; extraction_confidence: str | None = None

class DocumentUpdate(BaseModel):
    document_name: str | None = None; document_type: str | None = None; owner_name: str | None = None
    reference_number: str | None = None; issue_date: date | None = None; expiry_date: date | None = None
    notes: str | None = None; important_dates: str | None = None

class EventCreate(BaseModel):
    title: str; description: str | None = None; event_date: date; reminder_days: str = "7,3,1"
class EventUpdate(BaseModel):
    title: str | None = None; description: str | None = None; event_date: date | None = None; reminder_days: str | None = None
class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; title: str; description: str | None = None; event_date: date; reminder_days: str | None = None; created_at: datetime
class SearchResult(BaseModel):
    query: str; filters: dict[str, Any]; count: int; answer: str; documents: list[DocumentOut]


class LoginRequest(BaseModel):
    password: str


class BackupRestoreRequest(BaseModel):
    name: str
class SettingsUpdate(BaseModel):
    OPENAI_API_KEY: str | None = None; OPENAI_BASE_URL: str | None = None; OPENAI_MODEL: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None; TELEGRAM_CHAT_ID: str | None = None
    REMINDER_DAYS_DEFAULT: str | None = None; TIMEZONE: str | None = None
