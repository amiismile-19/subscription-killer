from datetime import datetime, timedelta, timezone
from database import get_db

def schedule_deadline_reminders(subscription_id, user_id, renewal_date=None, cancellation_deadline=None, custom_days=None):
    """
    Schedule reminders for subscription cancellation deadline according to user inputs.
    Uses either user-provided custom days or user's stored notification preferences.
    """
    db = get_db()

    # Determine reference date (prefer cancellation_deadline, fallback to renewal_date)
    target_date_str = cancellation_deadline or renewal_date
    if not target_date_str:
        return 0

    try:
        target_dt = datetime.strptime(target_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return 0

    # Get user reminder days preferences if not provided directly
    if custom_days is not None:
        reminder_days = [int(d) for d in custom_days]
    else:
        pref = db.execute("SELECT reminder_days FROM notification_preferences WHERE user_id=?", (user_id,)).fetchone()
        if pref and pref["reminder_days"]:
            try:
                reminder_days = [int(x.strip()) for x in pref["reminder_days"].split(",") if x.strip()]
            except ValueError:
                reminder_days = [7, 3, 1]
        else:
            reminder_days = [7, 3, 1]

    sub = db.execute("SELECT merchant, transaction_ref FROM subscriptions WHERE subscription_id=?", (subscription_id,)).fetchone()
    merchant = sub["merchant"] if sub else f"Subscription #{subscription_id}"
    txn_ref = sub["transaction_ref"] if sub else ""

    created = 0
    now = datetime.now(timezone.utc)

    for days in sorted(set(reminder_days), reverse=True):
        when = target_dt - timedelta(days=days)
        if when < now:
            # If reminder time already passed, create an immediate alert if deadline is still in future
            if target_dt > now and days == min(reminder_days):
                when = now + timedelta(seconds=10)
            else:
                continue

        if days == 0:
            title = f"🚨 URGENT: Cancellation Deadline TODAY for {merchant}"
            msg = f"Today is the deadline to cancel {merchant} (Txn ID: {txn_ref}) before recurring charge strikes."
        elif days == 1:
            title = f"⚠️ 24 Hours Left: Cancel {merchant}"
            msg = f"Only 1 day left to cancel {merchant} (Txn ID: {txn_ref}) before automatic renewal."
        else:
            title = f"📅 Deadline Reminder: {merchant} in {days} days"
            msg = f"{days} days remaining until cancellation deadline ({target_date_str}) for {merchant} (Txn ID: {txn_ref})."

        db.execute(
            """INSERT INTO notifications
               (user_id, subscription_id, transaction_ref, title, event_type, message, scheduled_at, status)
               VALUES (?, ?, ?, ?, 'cancellation_deadline', ?, ?, 'scheduled')""",
            (user_id, subscription_id, txn_ref, title, msg, when.isoformat())
        )
        created += 1

    db.commit()
    return created

def create_user_notification(user_id, message, title=None, scheduled_at=None,
                             subscription_id=None, transaction_ref=None, event_type="user_input_alert"):
    """
    Creates a notification specifically customized per user input.
    """
    db = get_db()
    if not scheduled_at:
        scheduled_at = datetime.now(timezone.utc).isoformat()
    if not title:
        title = "Personal Subscription Alert"

    cur = db.execute(
        """INSERT INTO notifications
           (user_id, subscription_id, transaction_ref, title, event_type, message, scheduled_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled')""",
        (user_id, subscription_id, transaction_ref, title, event_type, message, scheduled_at)
    )
    db.commit()
    return cur.lastrowid

def due_notifications():
    """
    Checks for due notifications and marks them as sent.
    """
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    rows = db.execute(
        "SELECT * FROM notifications WHERE status='scheduled' AND scheduled_at <= ?",
        (now,)
    ).fetchall()
    due_list = [dict(r) for r in rows]

    for row in due_list:
        db.execute(
            "UPDATE notifications SET status='sent', sent_at=? WHERE notification_id=?",
            (now, row["notification_id"])
        )
    db.commit()
    return due_list
