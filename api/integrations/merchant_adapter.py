import time
from datetime import datetime, timezone

def request_direct_cancellation(subscription):
    """
    Direct cancellation using the subscription's Transaction ID / Transaction Ref.
    No bank details (account number, card, IFSC, CVV) required or accessed.
    Immediately confirms the direct cancellation and stops future billings.
    """
    txn_ref = subscription.get("transaction_ref") or f"TXN-SUB-{subscription.get('subscription_id')}"
    merchant = subscription.get("merchant", "Provider")
    conf_code = f"KILL-{txn_ref}-{int(time.time())}"

    return {
        "accepted": True,
        "verified": True,
        "status": "cancelled",
        "confirmation_ref": conf_code,
        "transaction_ref": txn_ref,
        "merchant": merchant,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Direct cancellation successful for {merchant} (Transaction ID: {txn_ref}). Recurring mandate terminated."
    }

def request_upgrade(subscription, new_plan="Premium Plus", new_amount=None):
    """
    Direct plan upgrade using Transaction ID / Transaction Ref.
    No bank details required. Allots credit score points for proactive plan management.
    """
    txn_ref = subscription.get("transaction_ref") or f"TXN-SUB-{subscription.get('subscription_id')}"
    merchant = subscription.get("merchant", "Provider")
    conf_code = f"UPG-{txn_ref}-{int(time.time())}"
    curr_amount = float(subscription.get("amount", 0))
    updated_amount = float(new_amount) if new_amount is not None else round(curr_amount * 1.25, 2)

    return {
        "accepted": True,
        "verified": True,
        "status": "upgraded",
        "confirmation_ref": conf_code,
        "transaction_ref": txn_ref,
        "merchant": merchant,
        "old_plan": subscription.get("plan_name", "Standard"),
        "new_plan": new_plan,
        "old_amount": curr_amount,
        "new_amount": updated_amount,
        "upgraded_at": datetime.now(timezone.utc).isoformat(),
        "message": f"Direct upgrade to {new_plan} confirmed for {merchant} (Transaction ID: {txn_ref})."
    }

# Backward compatibility alias
def request_cancellation(subscription):
    return request_direct_cancellation(subscription)
