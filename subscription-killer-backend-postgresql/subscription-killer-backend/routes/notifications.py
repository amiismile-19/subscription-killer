from flask import Blueprint, jsonify, request
from database import get_db

bp = Blueprint("notifications", __name__)

@bp.get("/notifications")
def list_notifications():
    user_id = request.args.get("user_id", 1, type=int)
    rows = get_db().execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY scheduled_at DESC LIMIT 100",
        (user_id,)
    ).fetchall()
    return jsonify(notifications=[dict(r) for r in rows])

@bp.get("/notification-preferences")
def get_preferences():
    user_id = request.args.get("user_id", 1, type=int)
    row = get_db().execute("SELECT * FROM notification_preferences WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        return jsonify(error="Preferences not found"), 404
    return jsonify(preferences=dict(row))

@bp.put("/notification-preferences")
def update_preferences():
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))
    in_app = int(bool(data.get("in_app_enabled", True)))
    price_alerts = int(bool(data.get("price_alerts", True)))
    reminder_days = data.get("reminder_days", [7, 3, 1])
    if not isinstance(reminder_days, list) or any(not isinstance(x, int) or x < 0 or x > 365 for x in reminder_days):
        return jsonify(error="reminder_days must be a list of integers between 0 and 365"), 400
    db = get_db()
    db.execute(
        """INSERT INTO notification_preferences(user_id, in_app_enabled, price_alerts, reminder_days)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             in_app_enabled=excluded.in_app_enabled,
             price_alerts=excluded.price_alerts,
             reminder_days=excluded.reminder_days""",
        (user_id, in_app, price_alerts, ",".join(map(str, sorted(set(reminder_days), reverse=True))))
    )
    db.commit()
    return jsonify(ok=True, user_id=user_id, in_app_enabled=bool(in_app),
                   price_alerts=bool(price_alerts), reminder_days=sorted(set(reminder_days), reverse=True))
