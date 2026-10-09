from database import get_db

POINTS = {
    "subscription_cancelled": 50,
    "verified_cancellation": 50,
    "subscription_upgraded": 30,
    "verified_upgrade": 30,
    "verified_downgrade": 20,
    "avoided_renewal": 15,
    "budget_goal_met": 20,
    "baseline_onboarding": 50,
}

def award_points(user_id, subscription_id, action_type, idempotency_key, note=None, transaction_ref=None):
    if action_type not in POINTS:
        points = 25
    else:
        points = POINTS[action_type]

    db = get_db()
    try:
        db.execute(
            """INSERT INTO score_ledger
               (user_id, subscription_id, transaction_ref, action_type, points, idempotency_key, note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, subscription_id, transaction_ref, action_type, points, idempotency_key, note)
        )
        db.commit()
        user_score_data = get_user_score(user_id)
        return {
            "awarded": points,
            "duplicate": False,
            "action_type": action_type,
            "current_score": user_score_data["credit_score"],
            "rating_tier": user_score_data["tier"]
        }
    except Exception as exc:
        db.rollback()
        if "UNIQUE constraint failed" in str(exc):
            user_score_data = get_user_score(user_id)
            return {
                "awarded": 0,
                "duplicate": True,
                "action_type": action_type,
                "current_score": user_score_data["credit_score"],
                "rating_tier": user_score_data["tier"]
            }
        raise

def get_user_score(user_id=1):
    db = get_db()
    cur = db.execute("SELECT COALESCE(SUM(points), 0) AS total FROM score_ledger WHERE user_id=?", (user_id,))
    total_earned = cur.fetchone()["total"]

    # Baseline credit score scale: 650 initial base score + points earned, clamped to 300-900 range
    credit_score = min(900, max(300, 650 + int(total_earned)))

    # Rating tiers
    if credit_score >= 780:
        tier = "Excellent (Financial Master)"
        badge_color = "#10b981"
    elif credit_score >= 720:
        tier = "Very Good (Active Optimizer)"
        badge_color = "#3b82f6"
    elif credit_score >= 660:
        tier = "Good (Disciplined Subscriber)"
        badge_color = "#8b5cf6"
    elif credit_score >= 600:
        tier = "Fair (Building Discipline)"
        badge_color = "#f59e0b"
    else:
        tier = "Needs Review"
        badge_color = "#ef4444"

    # Action breakdowns
    cancellations = db.execute(
        """SELECT COUNT(*) as count, COALESCE(SUM(points), 0) as points
           FROM score_ledger
           WHERE user_id=? AND action_type IN ('subscription_cancelled', 'verified_cancellation')""",
        (user_id,)
    ).fetchone()

    upgrades = db.execute(
        """SELECT COUNT(*) as count, COALESCE(SUM(points), 0) as points
           FROM score_ledger
           WHERE user_id=? AND action_type IN ('subscription_upgraded', 'verified_upgrade')""",
        (user_id,)
    ).fetchone()

    # Total savings from cancelled subscriptions
    savings_row = db.execute(
        """SELECT COALESCE(SUM(amount), 0) as monthly_saved
           FROM subscriptions
           WHERE user_id=? AND status='cancelled'""",
        (user_id,)
    ).fetchone()

    return {
        "user_id": user_id,
        "credit_score": credit_score,
        "base_score": 650,
        "bonus_points_earned": total_earned,
        "tier": tier,
        "badge_color": badge_color,
        "cancellations_count": cancellations["count"],
        "cancellation_points": cancellations["points"],
        "upgrades_count": upgrades["count"],
        "upgrade_points": upgrades["points"],
        "monthly_saved": savings_row["monthly_saved"],
        "annual_saved": savings_row["monthly_saved"] * 12,
        "score_type": "Subscription Responsibility Credit Score (allotted on cancellations and upgrades)"
    }
