from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import settings
from database.db import SessionLocal
from services import reminder_service, report_service

def reminder_check_job():
    db = SessionLocal()
    try: reminder_service.sync_all_reminders(db); reminder_service.process_due_reminders(db)
    finally: db.close()
def daily_report_job():
    db = SessionLocal()
    try: report_service.send_daily_report(db)
    finally: db.close()
def create_scheduler():
    scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
    scheduler.add_job(daily_report_job, CronTrigger(hour=8, minute=0), id="daily_report", replace_existing=True)
    scheduler.add_job(reminder_check_job, IntervalTrigger(hours=1), id="reminders", replace_existing=True)
    return scheduler
