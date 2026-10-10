from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from database import get_db
from services.notifications import due_notifications, create_user_notification

bp = Blueprint("notifications", __name__)

@bp.get("/notifications")
def list_notifications():
    user_id = request.args.get("user_id", 1, type=int)
    status_filter = request.args.get("status")
    query = "SELECT * FROM notifications WHERE user_id=?"
    params = [user_id]
    if status_filter:
        query += " AND status=?"
        params.append(status_filter)
    query += " ORDER BY scheduled_at DESC LIMIT 100"

    rows = get_db().execute(query, params).fetchall()
    return jsonify(notifications=[dict(r) for r in rows], count=len(rows))

@bp.post("/notifications")
def create_custom_notification():
    """
    Create a notification directly as per user input.
    """
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify(error="message is required"), 400

    user_id = int(data.get("user_id", 1))
    title = str(data.get("title", "Custom Subscription Alert")).strip()
    scheduled_at = data.get("scheduled_at")
    subscription_id = data.get("subscription_id")
    transaction_ref = data.get("transaction_ref")
    event_type = data.get("event_type", "user_input_alert")

    notif_id = create_user_notification(
        user_id=user_id,
        message=message,
        title=title,
        scheduled_at=scheduled_at,
        subscription_id=subscription_id,
        transaction_ref=transaction_ref,
        event_type=event_type
    )

    created = get_db().execute("SELECT * FROM notifications WHERE notification_id=?", (notif_id,)).fetchone()
    return jsonify(success=True, notification=dict(created)), 201

@bp.get("/notification-preferences")
def get_preferences():
    user_id = request.args.get("user_id", 1, type=int)
    db = get_db()
    row = db.execute("SELECT * FROM notification_preferences WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        db.execute("INSERT OR IGNORE INTO notification_preferences(user_id) VALUES (?)", (user_id,))
        db.commit()
        row = db.execute("SELECT * FROM notification_preferences WHERE user_id=?", (user_id,)).fetchone()

    pref = dict(row)
    # Parse reminder days into clean integer array
    days_str = pref.get("reminder_days", "7,3,1")
    pref["reminder_days_list"] = [int(x.strip()) for x in days_str.split(",") if x.strip().isdigit()]
    return jsonify(preferences=pref)

@bp.put("/notification-preferences")
def update_preferences():
    """
    Update notification preferences per user input:
    reminder days, in-app alerts, audio voice alerts, and channels.
    """
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))
    in_app = int(bool(data.get("in_app_enabled", True)))
    audio_alerts = int(bool(data.get("audio_alerts", True)))
    price_alerts = int(bool(data.get("price_alerts", True)))

    reminder_days = data.get("reminder_days", [7, 3, 1])
    if isinstance(reminder_days, str):
        reminder_days = [int(x.strip()) for x in reminder_days.split(",") if x.strip().isdigit()]

    if not isinstance(reminder_days, list) or any(not isinstance(x, int) or x < 0 or x > 365 for x in reminder_days):
        return jsonify(error="reminder_days must be a list of integers between 0 and 365"), 400

    clean_days = sorted(set(reminder_days), reverse=True)
    preferred_channels = data.get("preferred_channels", "in_app,audio")
    if isinstance(preferred_channels, list):
        preferred_channels = ",".join(preferred_channels)

    db = get_db()
    db.execute(
        """INSERT INTO notification_preferences
           (user_id, in_app_enabled, audio_alerts, price_alerts, reminder_days, preferred_channels)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             in_app_enabled=excluded.in_app_enabled,
             audio_alerts=excluded.audio_alerts,
             price_alerts=excluded.price_alerts,
             reminder_days=excluded.reminder_days,
             preferred_channels=excluded.preferred_channels""",
        (user_id, in_app, audio_alerts, price_alerts, ",".join(map(str, clean_days)), preferred_channels)
    )
    db.commit()

    return jsonify(
        success=True,
        user_id=user_id,
        in_app_enabled=bool(in_app),
        audio_alerts=bool(audio_alerts),
        price_alerts=bool(price_alerts),
        reminder_days=clean_days,
        preferred_channels=preferred_channels.split(",")
    )

@bp.post("/notifications/trigger-due")
def trigger_due_notifications():
    """Check and deliver all due notifications immediately"""
    due_list = due_notifications()
    return jsonify(dispatched_count=len(due_list), notifications=due_list)

@bp.put("/notifications/<int:notification_id>/read")
def mark_read(notification_id):
    user_id = request.args.get("user_id", 1, type=int)
    db = get_db()
    db.execute("UPDATE notifications SET status='read' WHERE notification_id=? AND user_id=?", (notification_id, user_id))
    db.commit()
    return jsonify(success=True, notification_id=notification_id, status="read")

@bp.delete("/notifications/<int:notification_id>")
def delete_notification(notification_id):
    user_id = request.args.get("user_id", 1, type=int)
    db = get_db()
    db.execute("DELETE FROM notifications WHERE notification_id=? AND user_id=?", (notification_id, user_id))
    db.commit()
    return jsonify(success=True, message=f"Notification #{notification_id} deleted")
