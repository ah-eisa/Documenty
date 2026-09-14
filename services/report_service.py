from datetime import date
from database import repository

def build_daily_report_text(db):
    today = date.today(); documents = repository.list_documents(db, due_within_days=30, sort_by="expiry_date", order="asc"); overdue = repository.list_overdue_documents(db); events = repository.list_events(db, upcoming_days=30)
    lines = [f"Morning Report - {today.isoformat()}", "", "Expiring within 30 days:"]
    lines.extend(f"- {x.document_name or x.file_name} | {x.expiry_date}" for x in documents) or lines.append("- None")
    lines += ["", "Overdue:"]; lines.extend(f"- {x.document_name or x.file_name} | {x.expiry_date}" for x in overdue) or lines.append("- None")
    lines += ["", "Upcoming events:"]; lines.extend(f"- {x.title} | {x.event_date}" for x in events) or lines.append("- None")
    return "\n".join(lines)
def send_daily_report(db):
    from services.telegram_service import send_daily_report
    return send_daily_report(build_daily_report_text(db))
