from flask import Blueprint, jsonify, request
from database import get_db

bp = Blueprint("scores", __name__)

@bp.get("/score")
def get_score():
    user_id = request.args.get("user_id", 1, type=int)
    db = get_db()
    total = db.execute("SELECT COALESCE(SUM(points), 0) AS total FROM score_ledger WHERE user_id=?",
                       (user_id,)).fetchone()["total"]
    return jsonify(user_id=user_id, subscription_responsibility_score=max(0, min(1000, total)),
                   score_type="gamified platform score; not an official credit score")

@bp.get("/score/history")
def score_history():
    user_id = request.args.get("user_id", 1, type=int)
    rows = get_db().execute(
        "SELECT * FROM score_ledger WHERE user_id=? ORDER BY ledger_id DESC LIMIT 100", (user_id,)
    ).fetchall()
    return jsonify(entries=[dict(r) for r in rows])
