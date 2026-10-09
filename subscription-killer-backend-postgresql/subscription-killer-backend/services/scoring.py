from database import get_db

POINTS = {
    "verified_cancellation": 20,
    "verified_downgrade": 10,
    "verified_beneficial_upgrade": 5,
    "avoided_renewal": 5,
}

def award_points(user_id, subscription_id, action_type, idempotency_key, note=None):
    if action_type not in POINTS:
        raise ValueError("Unknown or ineligible score action")
    db = get_db()
    points = POINTS[action_type]
    try:
        db.execute(
            """INSERT INTO score_ledger
               (user_id, subscription_id, action_type, points, idempotency_key, note)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, subscription_id, action_type, points, idempotency_key, note)
        )
        db.commit()
        return {"awarded": points, "duplicate": False}
    except Exception as exc:
        db.rollback()
        if getattr(exc, "sqlstate", None) == "23505":
            return {"awarded": 0, "duplicate": True}
        raise
