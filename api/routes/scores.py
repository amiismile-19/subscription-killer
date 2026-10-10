from flask import Blueprint, jsonify, request
from database import get_db
from services.scoring import get_user_score, award_points

bp = Blueprint("scores", __name__)

@bp.get("/score")
def get_score():
    """
    Get user's Subscription Responsibility Credit Score.
    Points are allotted when the user cancels or upgrades subscriptions.
    """
    user_id = request.args.get("user_id", 1, type=int)
    score_data = get_user_score(user_id)
    return jsonify(score_data)

@bp.get("/score/history")
def score_history():
    """
    Ledger of all credit score points allotted for cancellations, upgrades, and savings.
    """
    user_id = request.args.get("user_id", 1, type=int)
    rows = get_db().execute(
        """SELECT ledger_id, user_id, subscription_id, transaction_ref, action_type, points, note, created_at
           FROM score_ledger
           WHERE user_id=?
           ORDER BY ledger_id DESC
           LIMIT 100""",
        (user_id,)
    ).fetchall()
    return jsonify(entries=[dict(r) for r in rows], count=len(rows))

@bp.post("/score/allot")
def manual_allot():
    """Admin or automated challenge score allotment"""
    data = request.get_json(silent=True) or {}
    user_id = int(data.get("user_id", 1))
    action_type = data.get("action_type", "budget_goal_met")
    subscription_id = data.get("subscription_id")
    transaction_ref = data.get("transaction_ref")
    note = data.get("note", "Financial milestone achieved")
    import time
    idempotency_key = data.get("idempotency_key", f"manual-{int(time.time()*1000)}")

    result = award_points(user_id, subscription_id, action_type, idempotency_key, note, transaction_ref)
    return jsonify(result)
