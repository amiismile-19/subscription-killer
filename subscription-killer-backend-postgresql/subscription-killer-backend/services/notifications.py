from datetime import datetime, timedelta, timezone
from database import get_db

def schedule_deadline_reminders(subscription_id, user_id, renewal_date, reminder_days=(7, 3, 1)):
    """Schedule in-app reminders relative to a YYYY-MM-DD renewal date."""
    if not renewal_date:
        return 0
    renewal = datetime.strptime(renewal_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    db = get_db()
    created = 0
    for days in reminder_days:
        when = renewal - timedelta(days=int(days))
        if when < datetime.now(timezone.utc):
            continue
        message = f"Subscription #{subscription_id} renews on {renewal_date}. Review cancellation options."
        db.execute(
            """INSERT INTO notifications(user_id, subscription_id, event_type, message, scheduled_at)
               VALUES (?, ?, 'renewal_reminder', ?, ?)""",
            (user_id, subscription_id, message, when.isoformat())
        )
        created += 1
    db.commit()
    return created

def due_notifications():
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    rows = db.execute(
        "SELECT * FROM notifications WHERE status='scheduled' AND scheduled_at <= ?",
        (now,)
    ).fetchall()
    for row in rows:
        # Demo mode delivers by making the alert visible through the API.
        db.execute(
            "UPDATE notifications SET status='sent', sent_at=? WHERE notification_id=?",
            (now, row["notification_id"])
        )
    db.commit()
    return len(rows)
