import asyncio

from booking_pricing import price_booking
import server


def test_flight_fare_breakdown_and_group_amount():
    amount = price_booking(
        "flight",
        {"price": 5200},
        quantity=2,
    )

    assert amount["subtotal"] == 10400
    assert amount["fees"] == 1726
    assert amount["gst_rate"] == 5
    assert amount["tax"] == 556.4
    assert amount["total"] == 12682.4
    assert amount["per_person"] == 6341.2
    assert amount["breakdown"][1]["label"] == "Fuel surcharge"


def test_sleeper_train_uses_zero_gst_and_promo():
    amount = price_booking(
        "train",
        {"price": 1000, "class": "Sleeper", "superfast": True},
        quantity=1,
        promo_code="WELCOME10",
    )

    assert amount["gst_rate"] == 0
    assert amount["discount"] == 100
    assert amount["tax"] == 0
    assert amount["total"] == 990


def test_hotel_uses_per_night_tariff_slab():
    amount = price_booking(
        "hotel",
        {"price_per_night": 9000},
        quantity=2,
        nights=2,
        rooms=1,
    )

    assert amount["subtotal"] == 18000
    assert amount["fees"] == 900
    assert amount["gst_rate"] == 18
    assert amount["tax"] == 3402
    assert amount["total"] == 22302


def test_invalid_promo_and_insurance_are_explicit():
    amount = price_booking(
        "bus",
        {"price": 1000},
        quantity=2,
        promo_code="NOTREAL",
        insurance=True,
    )

    assert amount["promo_valid"] is False
    assert amount["discount"] == 0
    assert amount["insurance"] is True
    assert any(row["label"] == "Optional travel insurance" for row in amount["breakdown"])


def test_plan_quote_aggregates_each_backend_priced_booking():
    request = server.ConfirmPlanRequest.model_validate({
        "items": [
            {"intent": "flight", "option_id": "F001", "quantity": 2},
            {"intent": "hotel", "option_id": "HTL002", "quantity": 2, "nights": 1, "rooms": 1},
        ],
    })

    quote = asyncio.run(server.confirm_plan(request))

    assert quote["amount"]["total"] == round(
        quote["items"][0]["preview"]["amount"]["total"]
        + quote["items"][1]["preview"]["amount"]["total"],
        2,
    )
    assert quote["amount"]["per_person"] == round(quote["amount"]["total"] / 2, 2)
    assert len(quote["items"]) == 2
