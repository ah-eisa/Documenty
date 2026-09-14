from __future__ import annotations
import os
from datetime import date
import pandas as pd
import requests
import streamlit as st
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DOCUMENT_TYPES = ["Passport", "Visa", "Insurance", "Contract", "Lease", "Bank Document", "Investment Document", "License", "Certificate", "Personal Document", "Other"]
st.set_page_config(page_title="Personal Operations Copilot", page_icon="DOC", layout="wide")

def api(method, path, **kwargs):
    try:
        response = requests.request(method, API_BASE_URL.rstrip("/") + path, timeout=300, **kwargs)
        if response.status_code >= 400:
            st.error(response.json().get("detail", response.text)); return None
        return response.json() if response.text else {}
    except requests.RequestException as exc:
        st.error(f"Backend unavailable: {exc}"); return None

def dashboard():
    st.title("Personal Operations Copilot")
    data = api("GET", "/api/dashboard")
    if not data: return
    cols = st.columns(6)
    for col, (label, key) in zip(cols, [("Documents", "documents_count"), ("Events", "events_count"), ("Due in 30 days", "expiring_30_count"), ("Overdue", "overdue_count"), ("Events in 30 days", "upcoming_events_30_count"), ("Critical", "critical_count")]): col.metric(label, data.get(key, 0))
    st.subheader("Latest alerts")
    st.dataframe(data.get("latest_alerts", []), use_container_width=True, hide_index=True)

def documents():
    st.title("Documents")
    with st.expander("Upload and process a document", expanded=True):
        uploaded = st.file_uploader("PDF, DOCX, XLSX, JPG, or PNG", type=["pdf", "docx", "xlsx", "jpg", "jpeg", "png"])
        if uploaded and st.button("Upload and process", type="primary"):
            result = api("POST", "/api/documents/upload", files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)})
            if result: st.success("Document processed"); st.rerun()
    left, middle, right = st.columns(3)
    query = left.text_input("Search")
    kind = middle.selectbox("Type", ["All"] + DOCUMENT_TYPES)
    due = right.number_input("Expiring within days", min_value=0, value=0)
    params = {"sort_by": "expiry_date", "order": "asc"}
    if query: params["q"] = query
    if kind != "All": params["document_type"] = kind
    if due: params["due_within_days"] = due
    rows = api("GET", "/api/documents", params=params)
    if rows is None: return
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if not rows: return
    selected = st.selectbox("Select document", rows, format_func=lambda x: f"{x['id']} - {x.get('document_name') or x['file_name']}")
    with st.form("edit_document"):
        name = st.text_input("Document name", selected.get("document_name") or "")
        owner = st.text_input("Owner", selected.get("owner_name") or "")
        reference = st.text_input("Reference", selected.get("reference_number") or "")
        expiry = st.text_input("Expiry date (YYYY-MM-DD)", selected.get("expiry_date") or "")
        notes = st.text_area("Notes", selected.get("notes") or "")
        if st.form_submit_button("Save changes"):
            if api("PUT", f"/api/documents/{selected['id']}", json={"document_name": name or None, "owner_name": owner or None, "reference_number": reference or None, "expiry_date": expiry or None, "notes": notes or None}): st.success("Saved"); st.rerun()
    if st.checkbox("Confirm document deletion") and st.button("Delete selected document"):
        if api("DELETE", f"/api/documents/{selected['id']}"): st.success("Deleted"); st.rerun()

def events():
    st.title("Events")
    with st.form("new_event"):
        title = st.text_input("Title"); description = st.text_area("Description"); event_date = st.date_input("Date", date.today()); reminders = st.text_input("Reminder days", "7,3,1")
        if st.form_submit_button("Add event", type="primary"):
            if title and api("POST", "/api/events", json={"title": title, "description": description or None, "event_date": event_date.isoformat(), "reminder_days": reminders}): st.success("Event added"); st.rerun()
    rows = api("GET", "/api/events", params={"sort_by": "event_date", "order": "asc"})
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

def search():
    st.title("Smart search")
    query = st.text_input("Ask about your documents", placeholder="Which documents expire within 30 days?")
    if st.button("Search", type="primary"):
        result = api("GET", "/api/search", params={"q": query})
        if result:
            st.info(result["answer"]); st.json(result["filters"]); st.dataframe(pd.DataFrame(result["documents"]), use_container_width=True, hide_index=True)

def settings_page():
    st.title("Settings")
    current = api("GET", "/api/settings")
    if not current: return
    with st.form("settings"):
        values = {}
        for key in ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "REMINDER_DAYS_DEFAULT", "TIMEZONE"]:
            values[key] = st.text_input(key, current.get(key, ""), type="password" if "KEY" in key or "TOKEN" in key else "default")
        if st.form_submit_button("Save settings", type="primary") and api("PUT", "/api/settings", json=values): st.success("Settings saved")
    if st.button("Send Telegram test"): api("POST", "/api/settings/test-telegram")

def main():
    page = st.sidebar.radio("Navigate", ["Dashboard", "Documents", "Events", "Smart search", "Settings"])
    {"Dashboard": dashboard, "Documents": documents, "Events": events, "Smart search": search, "Settings": settings_page}[page]()
if __name__ == "__main__": main()
