from datetime import datetime, date, time
from decimal import Decimal
from flask import Blueprint, request, jsonify
from database import get_db
from services.notifications import schedule_deadline_reminders

bp = Blueprint("subscriptions", __name__)

def rowdict(row):
    if not row:
        return None
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, (datetime, date, time)):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
    return result

@bp.post("")
def create_subscription():
    data = request.get_json(silent=True) or {}
    required = ("transaction_ref", "merchant", "amount")
    missing = [k for k in required if data.get(k) in (None, "")]
    if missing:
        return jsonify(error="Missing required fields", fields=missing), 400
    try:
        amount = float(data["amount"])
        if amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="amount must be a non-negative number"), 400
    renewal_date = data.get("renewal_date")
    if renewal_date:
        try:
            datetime.strptime(renewal_date, "%Y-%m-%d")
        except ValueError:
            return jsonify(error="renewal_date must use YYYY-MM-DD"), 400
    user_id = int(data.get("user_id", 1))
    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO subscriptions
               (user_id, transaction_ref, merchant, amount, currency, billing_frequency,
                renewal_date, cancellation_deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING subscription_id""",
            (user_id, str(data["transaction_ref"]).strip(), str(data["merchant"]).strip(),
             amount, data.get("currency", "INR"), data.get("billing_frequency", "monthly"),
             renewal_date, data.get("cancellation_deadline"))
        )
        subscription_id = cur.fetchone()["subscription_id"]
        db.execute("INSERT INTO notification_preferences(user_id) VALUES (?) ON CONFLICT(user_id) DO NOTHING", (user_id,))
        db.execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)",
                   (user_id, "subscription_created", f"subscription_id={subscription_id}"))
        db.commit()
    except Exception as exc:
        db.rollback()
        sqlstate = getattr(exc, "sqlstate", None)
        if sqlstate == "23505":
            return jsonify(error="This transaction reference already exists for this merchant and user"), 409
        if sqlstate == "23503":
            return jsonify(error="Unknown user_id; use the seeded demo user_id=1"), 400
        raise
    if renewal_date:
        schedule_deadline_reminders(subscription_id, user_id, renewal_date)
    row = db.execute("SELECT * FROM subscriptions WHERE subscription_id=?", (subscription_id,)).fetchone()
    return jsonify(subscription=rowdict(row)), 201

@bp.get("")
def list_subscriptions():
    user_id = request.args.get("user_id", "1", type=int)
    rows = get_db().execute(
        "SELECT * FROM subscriptions WHERE user_id=? ORDER BY subscription_id DESC", (user_id,)
    ).fetchall()
    return jsonify(subscriptions=[rowdict(r) for r in rows])

@bp.get("/<int:subscription_id>")
def get_subscription(subscription_id):
    user_id = request.args.get("user_id", "1", type=int)
    row = get_db().execute(
        "SELECT * FROM subscriptions WHERE subscription_id=? AND user_id=?",
        (subscription_id, user_id)
    ).fetchone()
    if not row:
        return jsonify(error="Subscription not found"), 404
    return jsonify(subscription=rowdict(row))
