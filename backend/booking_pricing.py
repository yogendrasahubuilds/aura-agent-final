"""Shared simulated pricing for booking previews and saved receipts."""
from simulated_rates import GST_RATES, SIMULATED_CHARGES

TRANSPORT_INTENTS = {"flight", "train", "bus"}


def _money(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def price_booking(
    intent: str,
    option: dict,
    quantity: int,
    nights: int = 1,
    rooms: int = 1,
    promo_code: str | None = None,
    insurance: bool = False,
) -> dict:
    quantity = max(1, int(quantity))
    nights = max(1, int(nights)) if intent == "hotel" else 1
    rooms = max(1, int(rooms)) if intent == "hotel" else 1
    charges = SIMULATED_CHARGES
    rows: list[dict] = []
    if intent == "hotel":
        base = float(option["price_per_night"]) * nights * rooms
        rows.append({"label": f"Room rate × {nights} night(s) × {rooms} room(s)", "amount": _money(base), "category": "base"})
        service = base * charges["hotel_service_percent"] / 100
        rows.append({"label": "Service charge", "amount": _money(service), "category": "fee"})
        gst_rate = next(rate for ceiling, rate in GST_RATES["hotel_slabs"] if float(option["price_per_night"]) <= ceiling)
        taxable = base + service
    else:
        unit = float(option["price"])
        base = unit * quantity
        rows.append({"label": "Base fare" if intent in TRANSPORT_INTENTS else "Ticket price", "amount": _money(base), "category": "base"})
        fees = 0.0
        if intent == "flight":
            fuel = base * charges["flight_fuel_percent"] / 100
            airport = charges["flight_airport_fee_per_passenger"] * quantity
            convenience = charges["flight_convenience_per_passenger"] * quantity
            for label, amount in (("Fuel surcharge", fuel), ("Airport user fee", airport), ("Convenience fee", convenience)):
                rows.append({"label": label, "amount": _money(amount), "category": "fee"})
                fees += amount
            gst_rate = GST_RATES["flight_percent"]
            taxable = base + fuel
        elif intent == "train":
            train_class = str(option.get("class", "")).lower()
            reservation = charges["train_reservation_per_passenger"] * quantity
            superfast = charges["train_superfast_per_passenger"] * quantity if option.get("superfast") else 0
            catering = next((amount for cls, amount in charges["train_catering_by_class"].items() if cls.lower() in train_class), 0) * quantity
            convenience = charges["train_convenience_per_passenger"] * quantity
            for label, amount in (("Reservation charge", reservation), ("Superfast charge", superfast), ("Catering", catering), ("Convenience fee", convenience)):
                rows.append({"label": label, "amount": _money(amount), "category": "fee"})
                fees += amount
            is_ac = any(marker in train_class for marker in ("ac", "1a", "2a", "3a", "cc", "ec"))
            gst_rate = GST_RATES["train_ac_percent"] if is_ac else GST_RATES["train_non_ac_percent"]
            taxable = base + fees
        elif intent == "bus":
            platform = charges["bus_platform_per_passenger"] * quantity
            rows.append({"label": "Platform fee", "amount": _money(platform), "category": "fee"})
            fees += platform
            gst_rate = GST_RATES["bus_percent"]
            taxable = base + fees
        elif intent in {"cricket", "concert", "movie"}:
            convenience = charges["event_convenience_per_ticket"] * quantity
            rows.append({"label": "Convenience fee", "amount": _money(convenience), "category": "fee"})
            fees += convenience
            gst_rate = GST_RATES["event_percent"]
            taxable = base + fees
        else:
            gst_rate = GST_RATES["event_percent"]
            taxable = base
        if insurance and intent in TRANSPORT_INTENTS:
            insurance_amount = charges["travel_insurance_per_passenger"] * quantity
            rows.append({"label": "Optional travel insurance", "amount": _money(insurance_amount), "category": "fee"})
            fees += insurance_amount
            taxable += insurance_amount

    subtotal = _money(base)
    fees_total = _money(sum(row["amount"] for row in rows if row["category"] == "fee"))
    discount = 0.0
    normalized_promo = (promo_code or "").strip().upper()
    promo = charges["promotions"].get(normalized_promo)
    if promo:
        discount = promo["value"] if promo["type"] == "fixed" else min(base * promo["value"] / 100, promo["maximum"])
        discount = min(_money(discount), _money(base + fees_total))
    tax = _money(max(0, taxable - discount) * gst_rate / 100)
    total = _money(max(0, subtotal + fees_total - discount + tax))
    rows.append({"label": f"GST ({gst_rate}%)", "amount": tax, "category": "tax"})
    return {
        "subtotal": subtotal,
        "fees": fees_total,
        "discount": _money(discount),
        "tax": tax,
        "gst_rate": gst_rate,
        "total": total,
        "currency": "INR",
        "breakdown": rows,
        "promo_code": normalized_promo or None,
        "promo_valid": not normalized_promo or promo is not None,
        "insurance": bool(insurance and intent in TRANSPORT_INTENTS),
        "per_person": _money(total / quantity),
    }
