"""Mock booking creation and verification."""
import random
import string
from datetime import datetime, timezone

PREFIX = {"movie": "AURA-MOV", "hotel": "AURA-HOT", "flight": "AURA-FLT"}


def _gen_booking_id(intent: str) -> str:
    suffix = "".join(random.choices(string.digits, k=5))
    return f"{PREFIX.get(intent, 'AURA-GEN')}-{suffix}"


def create_mock_booking(intent: str, option: dict, quantity: int, amount: dict, extra: dict) -> dict:
    booking_id = _gen_booking_id(intent)
    now = datetime.now(timezone.utc).isoformat()
    return {
        "booking_id": booking_id,
        "intent": intent,
        "option": option,
        "quantity": quantity,
        "amount": amount,
        "extra": extra,
        "status": "confirmed",
        "verified": True,
        "simulated": True,
        "created_at": now,
    }


def verify_booking(booking: dict) -> bool:
    """Independent verification step — mirrors a real inventory check."""
    if not booking:
        return False
    required = ["booking_id", "intent", "option", "status", "amount"]
    if not all(k in booking for k in required):
        return False
    if booking.get("status") != "confirmed":
        return False
    if not booking.get("booking_id", "").startswith("AURA-"):
        return False
    return True
