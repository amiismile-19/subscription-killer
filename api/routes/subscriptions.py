from datetime import datetime, timedelta, timezone
import random
from flask import Blueprint, request, jsonify
from database import get_db
from services.notifications import schedule_deadline_reminders

bp = Blueprint("subscriptions", __name__)

def rowdict(row):
    if not row:
        return None
    d = dict(row)
    if "amount" in d and d["amount"] is not None:
        try:
            d["amount"] = float(d["amount"])
        except (ValueError, TypeError):
            pass
    # Calculate days to deadline and urgency
    deadline_str = d.get("cancellation_deadline")
    if deadline_str:
        try:
            deadline_dt = datetime.strptime(deadline_str[:10], "%Y-%m-%d").date()
            today = datetime.now().date()
            days_left = (deadline_dt - today).days
            d["days_to_deadline"] = days_left
            if d.get("status") == "cancelled":
                d["deadline_urgency"] = "CANCELLED"
            elif days_left < 0:
                d["deadline_urgency"] = "EXPIRED"
            elif days_left <= 1:
                d["deadline_urgency"] = "CRITICAL"
            elif days_left <= 3:
                d["deadline_urgency"] = "WARNING"
            else:
                d["deadline_urgency"] = "UPCOMING"
        except Exception:
            d["days_to_deadline"] = None
            d["deadline_urgency"] = "UNKNOWN"
    else:
        d["days_to_deadline"] = None
        d["deadline_urgency"] = "NOT_SET"
    return d

@bp.post("")
def create_subscription():
    """
    Create a subscription working strictly from Transaction ID.
    No bank details (account numbers, card numbers, CVV) required or requested.
    """
    data = request.get_json(silent=True) or {}
    merchant = str(data.get("merchant", "")).strip()
    if not merchant:
        return jsonify(error="merchant is required"), 400

    try:
        amount = float(data.get("amount", 0))
        if amount < 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify(error="amount must be a non-negative number"), 400

    # Work directly from transaction_id / transaction_ref
    txn_ref = data.get("transaction_ref") or data.get("transaction_id")
    if not txn_ref:
        clean_name = "".join(c for c in merchant.upper() if c.isalnum())[:5] or "SUB"
        txn_ref = f"TXN-{clean_name}-{random.randint(1000, 9999)}"
    else:
        txn_ref = str(txn_ref).strip()

    user_id = int(data.get("user_id", 1))
    renewal_date = data.get("renewal_date")
    cancellation_deadline = data.get("cancellation_deadline")

    # Validate dates if provided
    if renewal_date:
        try:
            renewal_dt = datetime.strptime(renewal_date[:10], "%Y-%m-%d")
            # If no cancellation deadline provided by user, auto-calculate 2 days prior to renewal
            if not cancellation_deadline:
                cancellation_deadline = (renewal_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        except ValueError:
            return jsonify(error="renewal_date must use YYYY-MM-DD"), 400

    if cancellation_deadline:
        try:
            datetime.strptime(cancellation_deadline[:10], "%Y-%m-%d")
        except ValueError:
            return jsonify(error="cancellation_deadline must use YYYY-MM-DD"), 400

    plan_name = data.get("plan_name", "Standard")
    currency = data.get("currency", "INR")
    billing_frequency = data.get("billing_frequency", "monthly")

    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO subscriptions
               (user_id, transaction_ref, merchant, amount, currency, billing_frequency,
                plan_name, renewal_date, cancellation_deadline, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (user_id, txn_ref, merchant, amount, currency, billing_frequency,
             plan_name, renewal_date, cancellation_deadline)
        )
        subscription_id = cur.lastrowid
        db.execute("INSERT OR IGNORE INTO notification_preferences(user_id) VALUES (?)", (user_id,))
        db.execute("INSERT INTO audit_logs(user_id, action, details) VALUES (?, ?, ?)",
                   (user_id, "subscription_created", f"subscription_id={subscription_id}, txn={txn_ref}"))
        db.commit()
    except Exception as exc:
        db.rollback()
        if "UNIQUE constraint failed" in str(exc):
            return jsonify(error="This transaction ID already exists for this merchant and user", transaction_ref=txn_ref), 409
        if "FOREIGN KEY constraint failed" in str(exc):
            return jsonify(error="Unknown user_id; use seeded demo user_id=1"), 400
        raise

    # Auto-schedule cancellation deadline reminders per user's preference inputs
    custom_reminder_days = data.get("reminder_days")
    schedule_deadline_reminders(subscription_id, user_id, renewal_date, cancellation_deadline, custom_reminder_days)

    row = db.execute("SELECT * FROM subscriptions WHERE subscription_id=?", (subscription_id,)).fetchone()
    return jsonify(subscription=rowdict(row)), 201

@bp.get("")
def list_subscriptions():
    user_id = request.args.get("user_id", 1, type=int)
    status_filter = request.args.get("status")
    search = request.args.get("search", "").strip().lower()

    query = "SELECT * FROM subscriptions WHERE user_id=?"
    params = [user_id]

    if status_filter:
        query += " AND status=?"
        params.append(status_filter)

    query += " ORDER BY subscription_id DESC"
    rows = get_db().execute(query, params).fetchall()

    result = [rowdict(r) for r in rows]
    if search:
        result = [s for s in result if search in s["merchant"].lower() or search in s["transaction_ref"].lower()]

    return jsonify(subscriptions=result, count=len(result))

@bp.get("/<int:subscription_id>")
def get_subscription(subscription_id):
    user_id = request.args.get("user_id", 1, type=int)
    row = get_db().execute(
        "SELECT * FROM subscriptions WHERE subscription_id=? AND user_id=?",
        (subscription_id, user_id)
    ).fetchone()
    if not row:
        return jsonify(error="Subscription not found"), 404
    return jsonify(subscription=rowdict(row))

@bp.get("/by-transaction/<string:transaction_ref>")
def get_subscription_by_transaction(transaction_ref):
    """Direct lookup using Transaction ID without any bank details"""
    user_id = request.args.get("user_id", 1, type=int)
    row = get_db().execute(
        "SELECT * FROM subscriptions WHERE transaction_ref=? AND user_id=?",
        (transaction_ref.strip(), user_id)
    ).fetchone()
    if not row:
        return jsonify(error=f"No subscription found with Transaction ID '{transaction_ref}'"), 404
    return jsonify(subscription=rowdict(row))

@bp.put("/<int:subscription_id>")
def update_subscription(subscription_id):
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))
    db = get_db()
    sub = db.execute("SELECT * FROM subscriptions WHERE subscription_id=? AND user_id=?",
                     (subscription_id, user_id)).fetchone()
    if not sub:
        return jsonify(error="Subscription not found"), 404

    amount = data.get("amount", sub["amount"])
    plan_name = data.get("plan_name", sub["plan_name"])
    renewal_date = data.get("renewal_date", sub["renewal_date"])
    cancellation_deadline = data.get("cancellation_deadline", sub["cancellation_deadline"])

    db.execute(
        """UPDATE subscriptions
           SET amount=?, plan_name=?, renewal_date=?, cancellation_deadline=?
           WHERE subscription_id=? AND user_id=?""",
        (amount, plan_name, renewal_date, cancellation_deadline, subscription_id, user_id)
    )
    db.commit()

    if renewal_date or cancellation_deadline:
        schedule_deadline_reminders(subscription_id, user_id, renewal_date, cancellation_deadline)

    updated = db.execute("SELECT * FROM subscriptions WHERE subscription_id=?", (subscription_id,)).fetchone()
    return jsonify(subscription=rowdict(updated))

@bp.delete("/<int:subscription_id>")
def delete_subscription(subscription_id):
    user_id = request.args.get("user_id", 1, type=int)
    db = get_db()
    cur = db.execute("DELETE FROM subscriptions WHERE subscription_id=? AND user_id=?", (subscription_id, user_id))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Subscription not found"), 404
    return jsonify(ok=True, message=f"Subscription #{subscription_id} deleted")

@bp.post("/batch")
def batch_create_subscriptions():
    """
    Import/Sync a list of detected subscriptions directly into the database.
    Operates strictly with Transaction IDs; no bank details required.
    """
    data = request.get_json(silent=True) or {}
    items = data.get("subscriptions", [])
    user_id = int(data.get("user_id", 1))

    if not isinstance(items, list):
        return jsonify(error="subscriptions must be a list"), 400

    db = get_db()
    saved = []
    for item in items:
        merchant = str(item.get("merchant") or item.get("name", "")).strip()
        if not merchant:
            continue

        amount = float(item.get("amount") or item.get("last", 0))
        txn_ref = item.get("transaction_ref") or item.get("transaction_id") or item.get("id")
        if not txn_ref or not str(txn_ref).startswith("TXN-"):
            clean_name = "".join(c for c in merchant.upper() if c.isalnum())[:5] or "SUB"
            txn_ref = f"TXN-{clean_name}-{random.randint(1000, 9999)}"

        plan_name = item.get("plan_name") or item.get("plan", "Standard")
        billing_freq = item.get("billing_frequency")
        if not billing_freq:
            f = item.get("f", "M")
            billing_freq = "annual" if f == "A" else ("weekly" if f == "W" else "monthly")

        renewal_date = item.get("renewal_date")
        if not renewal_date and item.get("a") and isinstance(item["a"], list) and len(item["a"]) > 0:
            last_dt = item["a"][-1].get("d") if isinstance(item["a"][-1], dict) else None
            if last_dt:
                try:
                    # Next renewal is roughly 30 days after last payment
                    from datetime import datetime, timedelta
                    dt_obj = datetime.fromisoformat(str(last_dt).replace("Z", ""))
                    renewal_date = (dt_obj + timedelta(days=30)).strftime("%Y-%m-%d")
                except Exception:
                    pass

        if not renewal_date:
            from datetime import datetime, timedelta
            renewal_date = (datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d")

        cancellation_deadline = item.get("cancellation_deadline")
        if not cancellation_deadline:
            from datetime import datetime, timedelta
            try:
                r_dt = datetime.strptime(renewal_date[:10], "%Y-%m-%d")
                cancellation_deadline = (r_dt - timedelta(days=2)).strftime("%Y-%m-%d")
            except Exception:
                cancellation_deadline = renewal_date

        # Insert or update
        existing = db.execute(
            "SELECT * FROM subscriptions WHERE user_id=? AND (transaction_ref=? OR merchant=?)",
            (user_id, str(txn_ref), merchant)
        ).fetchone()

        if existing:
            db.execute(
                """UPDATE subscriptions
                   SET amount=?, plan_name=?, billing_frequency=?, renewal_date=?, cancellation_deadline=?
                   WHERE subscription_id=?""",
                (amount, plan_name, billing_freq, renewal_date, cancellation_deadline, existing["subscription_id"])
            )
            sub_id = existing["subscription_id"]
        else:
            cur = db.execute(
                """INSERT INTO subscriptions
                   (user_id, transaction_ref, merchant, amount, currency, billing_frequency,
                    plan_name, renewal_date, cancellation_deadline, status)
                   VALUES (?, ?, ?, ?, 'INR', ?, ?, ?, ?, 'active')""",
                (user_id, str(txn_ref), merchant, amount, billing_freq, plan_name, renewal_date, cancellation_deadline)
            )
            sub_id = cur.lastrowid

        schedule_deadline_reminders(sub_id, user_id, renewal_date, cancellation_deadline)
        row = db.execute("SELECT * FROM subscriptions WHERE subscription_id=?", (sub_id,)).fetchone()
        saved.append(rowdict(row))

    db.commit()
    return jsonify(subscriptions=saved, count=len(saved)), 200

