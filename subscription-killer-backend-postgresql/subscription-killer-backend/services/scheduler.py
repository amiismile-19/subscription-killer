from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from services.notifications import due_notifications

_scheduler = None

def start_scheduler(app):
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    scheduler = BackgroundScheduler(daemon=True)
    def job():
        with app.app_context():
            due_notifications()
    scheduler.add_job(job, "interval", seconds=30, id="notification-dispatch", replace_existing=True)
    scheduler.start()
    _scheduler = scheduler
