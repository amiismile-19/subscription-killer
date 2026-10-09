"""Demo merchant adapter. Replace with official merchant/provider integrations."""
import os

def request_cancellation(subscription):
    """
    In demo mode, simulate accepting a request but do NOT claim the merchant
    subscription was actually cancelled. Real cancellation requires an authorized
    merchant API or a user-completed cancellation flow.
    """
    mode = os.getenv("APP_MODE", "demo").lower()
    if mode == "demo":
        return {
            "accepted": True,
            "verified": False,
            "status": "requested",
            "confirmation_ref": f"DEMO-CANCEL-{subscription['subscription_id']}",
            "message": "Demo request recorded; merchant cancellation is not verified."
        }
    return {
        "accepted": False,
        "verified": False,
        "status": "manual_action_required",
        "confirmation_ref": None,
        "message": "No merchant adapter configured. Open the merchant's official cancellation flow."
    }
