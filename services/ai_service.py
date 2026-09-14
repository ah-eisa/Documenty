from __future__ import annotations
import json, logging, re
from datetime import date, datetime
from pathlib import Path
from typing import Any
import httpx
from dateutil import parser as date_parser
from config import settings
logger = logging.getLogger(__name__)
DOC_TYPES = ["Passport", "Visa", "Insurance", "Contract", "Lease", "Bank Document", "Investment Document", "License", "Certificate", "Personal Document", "Other"]
KEYWORDS = {"Passport": ["passport", "جواز"], "Visa": ["visa", "تأشيرة", "تاشيرة"], "Insurance": ["insurance", "تأمين", "تامين"], "Contract": ["contract", "عقد"], "Lease": ["lease", "إيجار", "ايجار"], "Bank Document": ["bank", "بنك", "statement"], "Investment Document": ["investment", "استثمار", "portfolio"], "License": ["license", "رخصة", "ترخيص"], "Certificate": ["certificate", "شهادة"], "Personal Document": ["personal", "هوية", "identity"]}

def parse_date_to_iso(value: Any):
    if value is None: return None
    if isinstance(value, datetime): return value.date().isoformat()
    if isinstance(value, date): return value.isoformat()
    text = str(value).strip().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    if not text: return None
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match: return match.group(1)
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y", "%d.%m.%Y"):
        try: return datetime.strptime(text, fmt).date().isoformat()
        except ValueError: pass
    try: return date_parser.parse(text, fuzzy=True).date().isoformat()
    except Exception: return None

def normalize_doc_type(value, default="Other"):
    text = str(value or "").lower()
    for kind in DOC_TYPES:
        if text == kind.lower() or any(word in text for word in KEYWORDS.get(kind, [])): return kind
    return default

def _call_llm(messages):
    if not settings.OPENAI_API_KEY: return None
    try:
        response = httpx.post(f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}, json={"model": settings.OPENAI_MODEL, "messages": messages, "temperature": 0}, timeout=180)
        response.raise_for_status(); return response.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("AI extraction request failed: %s", exc)
        return None

def _heuristic(text):
    lowered = text.lower(); kind = next((k for k, words in KEYWORDS.items() if any(w.lower() in lowered for w in words)), "Other")
    dates = sorted({d for m in re.finditer(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})\b", text) if (d := parse_date_to_iso(m.group()))})
    expiry = next((parse_date_to_iso(m.group()) for line in text.splitlines() if any(x in line.lower() for x in ["expiry", "expiration", "انتهاء"]) for m in re.finditer(r"\d{1,4}[/.-]\d{1,2}[/.-]\d{2,4}", line)), None)
    return {"document_type": kind, "owner_name": None, "issue_date": dates[0] if len(dates) > 1 else None, "expiry_date": expiry or (dates[-1] if dates else None), "reference_number": None, "important_dates": [{"label": "Detected date", "date": d} for d in dates], "notes": None}

def extract_document_info(text, file_name):
    heuristic = _heuristic(text or "")
    prompt = f"Extract JSON with document_type, owner_name, issue_date, expiry_date, reference_number, important_dates, notes from this text. Types: {DOC_TYPES}. Dates YYYY-MM-DD.\n{text[:settings.MAX_AI_TEXT_CHARS]}"
    raw = _call_llm([{"role": "system", "content": "Return only valid JSON."}, {"role": "user", "content": prompt}])
    try:
        parsed = json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    data = dict(heuristic)
    for key in heuristic:
        value = parsed.get(key)
        if key == "important_dates" and isinstance(value, list):
            data[key] = value
        elif key != "important_dates" and isinstance(value, (str, int, float)) and str(value).strip():
            data[key] = value
    data["document_type"] = normalize_doc_type(data.get("document_type"))
    data["issue_date"] = parse_date_to_iso(data.get("issue_date"))
    data["expiry_date"] = parse_date_to_iso(data.get("expiry_date"))
    data["document_name"] = Path(file_name).stem
    data["source"] = "ai+heuristic" if parsed else "heuristic"
    data["confidence"] = "medium" if parsed else "low"
    return data

def parse_search_query(query):
    lowered = (query or "").lower().translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")); filters = {"q": None, "document_type": None, "expiry_within_days": None, "expiry_year": None, "sort_by": "expiry_date", "order": "asc"}
    for kind, words in KEYWORDS.items():
        if any(word.lower() in lowered for word in words): filters["document_type"] = kind; break
    days = re.search(r"(\d+)\s*(?:يوم|days?|day)", lowered)
    if days: filters["expiry_within_days"] = int(days.group(1))
    year = re.search(r"\b(20\d{2})\b", lowered)
    if year: filters["expiry_year"] = int(year.group(1))
    if any(word in lowered for word in ["latest", "recent", "أحدث"]): filters.update(sort_by="created_at", order="desc")
    return filters
