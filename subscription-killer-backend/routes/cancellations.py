import time
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from database import get_db
from integrations.merchant_adapter import request_direct_cancellation, request_upgrade
from services.scoring import award_points, get_user_score

bp = Blueprint("cancellations", __name__)

def calc_deadline_details(sub):
    """Calculate deadline, days/hours remaining, and urgency for a subscription"""
    deadline_str = sub.get("cancellation_deadline")
    renewal_str = sub.get("renewal_date")
    status = sub.get("status")

    if not deadline_str and renewal_str:
        try:
            r_dt = datetime.strptime(renewal_str[:10], "%Y-%m-%d")
            # Default deadline is 2 days before renewal
            from datetime import timedelta
            deadline_str = (r_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        except Exception:
            deadline_str = renewal_str

    days_remaining = None
    hours_remaining = None
    urgency = "UNKNOWN"
    recommendation = "Review subscription status"

    if deadline_str:
        try:
            dl_dt = datetime.strptime(deadline_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            diff = dl_dt - now
            days_remaining = diff.days
            hours_remaining = max(0, int(diff.total_seconds() // 3600))

            if status == "cancelled":
                urgency = "CANCELLED"
                recommendation = "Subscription is already directly cancelled. No action required."
            elif diff.total_seconds() < 0:
                urgency = "EXPIRED"
                recommendation = "Deadline has passed. Cancel now to avoid next renewal cycle."
            elif days_remaining <= 1:
                urgency = "CRITICAL"
                recommendation = f"URGENT: Only {hours_remaining} hours remaining. Direct cancellation recommended immediately."
            elif days_remaining <= 3:
                urgency = "WARNING"
                recommendation = f"Upcoming deadline in {days_remaining} days. Decide if you wish to retain or kill."
            else:
                urgency = "UPCOMING"
                recommendation = f"Safe buffer: {days_remaining} days until deadline ({deadline_str})."
        except Exception:
            pass

    return {
        "subscription_id": sub.get("subscription_id"),
        "merchant": sub.get("merchant"),
        "transaction_ref": sub.get("transaction_ref"),
        "amount": sub.get("amount"),
        "billing_frequency": sub.get("billing_frequency"),
        "renewal_date": renewal_str,
        "cancellation_deadline": deadline_str,
        "days_remaining": days_remaining,
        "hours_remaining": hours_remaining,
        "urgency": urgency,
        "status": status,
        "recommendation": recommendation,
        "can_direct_cancel": status != "cancelled"
    }

@bp.post("/subscriptions/<int:subscription_id>/cancel")
def cancel_subscription(subscription_id):
    """
    Direct cancellation of subscription using Transaction ID.
    No bank details required. Immediately terminates the subscription,
    generates cancellation confirmation, and allots credit score points!
    """
    db = get_db()
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))

    subscription = db.execute(
        "SELECT * FROM subscriptions WHERE subscription_id=? AND user_id=?",
        (subscription_id, user_id)
    ).fetchone()
    if not subscription:
        return jsonify(error="Subscription not found"), 404

    sub = dict(subscription)
    if sub["status"] == "cancelled":
        return jsonify(
            error="Subscription is already cancelled",
            status="cancelled",
            transaction_ref=sub["transaction_ref"]
        ), 409

    # Execute direct cancellation via transaction_ref
    result = request_direct_cancellation(sub)

    # Directly mark as cancelled in database
    db.execute("UPDATE subscriptions SET status='cancelled' WHERE subscription_id=?", (subscription_id,))
    cur = db.execute(
        """INSERT INTO cancellation_requests
           (subscription_id, transaction_ref, status, confirmation_ref, message)
           VALUES (?, ?, 'cancelled', ?, ?)""",
        (subscription_id, sub["transaction_ref"], result["confirmation_ref"], result["message"])
    )

    # Log audit trail
    db.execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)",
               (user_id, "direct_cancellation", f"subscription_id={subscription_id}, txn={sub['transaction_ref']}"))

    # Create in-app notification confirming direct cancellation
    db.execute(
        """INSERT INTO notifications
           (user_id, subscription_id, transaction_ref, title, event_type, message, scheduled_at, sent_at, status)
           VALUES (?, ?, ?, '✅ Direct Cancellation Confirmed', 'cancellation_confirmed', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'sent')""",
        (user_id, subscription_id, sub["transaction_ref"],
         f"{sub['merchant']} directly cancelled. Ref: {result['confirmation_ref']}. Points allotted to your score!")
    )
    db.commit()

    # Allot credit score points immediately (+50 points)
    reward = award_points(
        user_id=user_id,
        subscription_id=subscription_id,
        action_type="subscription_cancelled",
        idempotency_key=f"cancel-txn-{sub['transaction_ref']}-{int(time.time())}",
        note=f"Direct cancellation of {sub['merchant']} (Txn: {sub['transaction_ref']})",
        transaction_ref=sub["transaction_ref"]
    )

    return jsonify(
        success=True,
        action="direct_cancellation",
        subscription_id=subscription_id,
        transaction_ref=sub["transaction_ref"],
        subscription_status="cancelled",
        confirmation_code=result["confirmation_ref"],
        merchant=sub["merchant"],
        monthly_saved=float(sub["amount"]) if sub["amount"] is not None else 0.0,
        points_awarded=reward["awarded"],
        current_credit_score=reward["current_score"],
        credit_rating_tier=reward["rating_tier"],
        receipt=result
    ), 200

@bp.post("/subscriptions/cancel-by-transaction")
def cancel_by_transaction():
    """
    Direct cancellation strictly via Transaction ID without requiring subscription ID or bank details.
    """
    data = request.get_json(silent=True) or {}
    txn_ref = data.get("transaction_ref") or data.get("transaction_id")
    if not txn_ref:
        return jsonify(error="transaction_ref or transaction_id is required"), 400

    user_id = int(data.get("user_id", 1))
    db = get_db()
    subscription = db.execute(
        "SELECT * FROM subscriptions WHERE transaction_ref=? AND user_id=?",
        (str(txn_ref).strip(), user_id)
    ).fetchone()
    if not subscription:
        return jsonify(error=f"No subscription found with Transaction ID '{txn_ref}'"), 404

    return cancel_subscription(subscription["subscription_id"])

@bp.post("/subscriptions/<int:subscription_id>/upgrade")
def upgrade_subscription(subscription_id):
    """
    Upgrade subscription plan. Allots credit score points for proactive upgrade!
    """
    db = get_db()
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))
    new_plan = str(data.get("new_plan", "Premium Plus")).strip()
    new_amount = data.get("new_amount")

    subscription = db.execute(
        "SELECT * FROM subscriptions WHERE subscription_id=? AND user_id=?",
        (subscription_id, user_id)
    ).fetchone()
    if not subscription:
        return jsonify(error="Subscription not found"), 404

    sub = dict(subscription)
    if sub["status"] == "cancelled":
        return jsonify(error="Cannot upgrade a cancelled subscription"), 400

    result = request_upgrade(sub, new_plan, new_amount)

    db.execute(
        "UPDATE subscriptions SET plan_name=?, amount=?, status='active' WHERE subscription_id=?",
        (result["new_plan"], result["new_amount"], subscription_id)
    )
    db.execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)",
               (user_id, "subscription_upgraded", f"subscription_id={subscription_id}, new_plan={new_plan}"))

    # Create notification for upgrade
    db.execute(
        """INSERT INTO notifications
           (user_id, subscription_id, transaction_ref, title, event_type, message, scheduled_at, sent_at, status)
           VALUES (?, ?, ?, '⭐ Plan Upgraded', 'subscription_upgraded', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'sent')""",
        (user_id, subscription_id, sub["transaction_ref"],
         f"{sub['merchant']} upgraded to {result['new_plan']} (₹{result['new_amount']}). Credit score points awarded!")
    )
    db.commit()

    # Allot credit score points immediately (+30 points)
    reward = award_points(
        user_id=user_id,
        subscription_id=subscription_id,
        action_type="subscription_upgraded",
        idempotency_key=f"upgrade-txn-{sub['transaction_ref']}-{int(time.time())}",
        note=f"Proactive upgrade of {sub['merchant']} to {result['new_plan']}",
        transaction_ref=sub["transaction_ref"]
    )

    return jsonify(
        success=True,
        action="subscription_upgrade",
        subscription_id=subscription_id,
        transaction_ref=sub["transaction_ref"],
        old_plan=result["old_plan"],
        new_plan=result["new_plan"],
        new_amount=result["new_amount"],
        confirmation_code=result["confirmation_ref"],
        points_awarded=reward["awarded"],
        current_credit_score=reward["current_score"],
        credit_rating_tier=reward["rating_tier"]
    ), 200

@bp.post("/subscriptions/upgrade-by-transaction")
def upgrade_by_transaction():
    data = request.get_json(silent=True) or {}
    txn_ref = data.get("transaction_ref") or data.get("transaction_id")
    if not txn_ref:
        return jsonify(error="transaction_ref or transaction_id is required"), 400

    user_id = int(data.get("user_id", 1))
    db = get_db()
    subscription = db.execute(
        "SELECT * FROM subscriptions WHERE transaction_ref=? AND user_id=?",
        (str(txn_ref).strip(), user_id)
    ).fetchone()
    if not subscription:
        return jsonify(error=f"No subscription found with Transaction ID '{txn_ref}'"), 404

    return upgrade_subscription(subscription["subscription_id"])

@bp.get("/subscriptions/<int:subscription_id>/deadline")
def get_deadline(subscription_id):
    """Get precise cancellation deadline details for a subscription"""
    row = get_db().execute(
        "SELECT * FROM subscriptions WHERE subscription_id=?",
        (subscription_id,)
    ).fetchone()
    if not row:
        return jsonify(error="Subscription not found"), 404
    return jsonify(deadline=calc_deadline_details(dict(row)))

@bp.get("/subscriptions/deadlines")
def list_deadlines():
    """List cancellation deadlines for all subscriptions, sorted by nearest deadline first"""
    user_id = request.args.get("user_id", 1, type=int)
    rows = get_db().execute(
        "SELECT * FROM subscriptions WHERE user_id=? ORDER BY cancellation_deadline ASC, renewal_date ASC",
        (user_id,)
    ).fetchall()

    deadlines = [calc_deadline_details(dict(r)) for r in rows]
    # Filter active/upcoming
    active_deadlines = [d for d in deadlines if d["status"] != "cancelled"]

    critical_count = sum(1 for d in active_deadlines if d["urgency"] == "CRITICAL")
    warning_count = sum(1 for d in active_deadlines if d["urgency"] == "WARNING")

    return jsonify(
        deadlines=deadlines,
        total=len(deadlines),
        critical_count=critical_count,
        warning_count=warning_count
    )

@bp.put("/subscriptions/<int:subscription_id>/deadline")
def update_deadline(subscription_id):
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))
    new_deadline = data.get("cancellation_deadline")
    if not new_deadline:
        return jsonify(error="cancellation_deadline is required (YYYY-MM-DD)"), 400

    try:
        datetime.strptime(new_deadline[:10], "%Y-%m-%d")
    except ValueError:
        return jsonify(error="cancellation_deadline must be YYYY-MM-DD"), 400

    db = get_db()
    cur = db.execute(
        "UPDATE subscriptions SET cancellation_deadline=? WHERE subscription_id=? AND user_id=?",
        (new_deadline, subscription_id, user_id)
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Subscription not found"), 404

    row = db.execute("SELECT * FROM subscriptions WHERE subscription_id=?", (subscription_id,)).fetchone()
    return jsonify(deadline=calc_deadline_details(dict(row)))
