from flask import Blueprint, jsonify
from database import get_db
from integrations.merchant_adapter import request_cancellation
from services.scoring import award_points

bp = Blueprint("cancellations", __name__)

@bp.post("/subscriptions/<int:subscription_id>/cancel")
def cancel_subscription(subscription_id):
    db = get_db()
    user_id = 1
    subscription = db.execute(
        "SELECT * FROM subscriptions WHERE subscription_id=? AND user_id=?",
        (subscription_id, user_id)
    ).fetchone()
    if not subscription:
        return jsonify(error="Subscription not found"), 404
    sub = dict(subscription)
    if sub["status"] in ("cancelled", "cancellation_requested"):
        return jsonify(error="Cancellation already requested or completed", status=sub["status"]), 409
    result = request_cancellation(sub)
    if not result["accepted"]:
        return jsonify(result), 501
    status = "cancellation_requested" if not result.get("verified") else "cancelled"
    db.execute("UPDATE subscriptions SET status=? WHERE subscription_id=?", (status, subscription_id))
    cur = db.execute(
        """INSERT INTO cancellation_requests(subscription_id, status, confirmation_ref, message)
           VALUES (?, ?, ?, ?)""",
        (subscription_id, result["status"], result.get("confirmation_ref"), result.get("message"))
    )
    db.execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)",
               (user_id, "cancellation_requested", f"subscription_id={subscription_id}"))
    db.commit()
    reward = {"awarded": 0, "duplicate": False}
    if result.get("verified"):
        reward = award_points(user_id, subscription_id, "verified_cancellation",
                              f"verified-cancel-{subscription_id}")
    return jsonify(
        cancellation_request_id=cur.lastrowid,
        subscription_status=status,
        merchant_result=result,
        score_reward=reward
    ), 202

@bp.get("/subscriptions/<int:subscription_id>/deadline")
def get_deadline(subscription_id):
    row = get_db().execute(
        "SELECT subscription_id, renewal_date, cancellation_deadline, status FROM subscriptions WHERE subscription_id=?",
        (subscription_id,)
    ).fetchone()
    if not row:
        return jsonify(error="Subscription not found"), 404
    return jsonify(deadline=dict(row))
