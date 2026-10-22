from datetime import date, datetime

import pytest

import server
from destination_data import generateDestinationHotels
from trip_planner import build_destination_trip, extract_destination_request


def test_destination_trip_defaults_routes_and_budget_are_tool_grounded():
    text = "Plan a 4 day trip to Manali from Raipur for 2 people under 25000 starting 20 October 2026"
    plan = build_destination_trip(
        extract_destination_request(text, today=date(2026, 10, 19)),
        text,
    )

    assert plan["details"]["nights"] == 3
    assert plan["details"]["travelers"] == 2
    assert plan["details"]["rooms"] == 1
    assert plan["details"]["preference"] == "comfort"
    assert len(plan["route_legs"]) >= 2
    assert len(plan["options"]["trip_route"]) == 3
    assert len(plan["options"]["hotel"]) == 3
    assert sum(option["recommended"] for option in plan["options"]["hotel"]) == 1
    assert abs(
        plan["grand_total"]
        - sum(plan["cost_breakdown"][part] for part in (
            "transport", "last_mile", "stay", "daily", "taxes_fees",
        ))
    ) <= 0.01
    assert plan["budget_status"]["over_budget"] is True
    assert plan["budget_status"]["minimum_needed"] <= plan["grand_total"]
    assert len(generateDestinationHotels("Manali")) == 8

    for leg in plan["route_legs"]:
        option = leg.get("option")
        if option:
            departure = datetime.fromisoformat(f"{option['date']}T{option['departure']}")
            arrival = datetime.fromisoformat(f"{option['arrival_date']}T{option['arrival']}")
            assert arrival >= departure


def test_destination_trip_chat_asks_only_missing_required_fields(monkeypatch):
    monkeypatch.setattr(server, "db", server.InMemoryDatabase())
    user = {"id": "destination-trip-test", "name": "Test"}

    async def ask(message, conversation):
        return await server.chat(
            server.ChatRequest(
                message=message,
                user_id=user["id"],
                mode="conversation",
                conversation=conversation,
            ),
            current_user=user,
        )

    async def exercise():
        first = await ask("Plan a trip to Goa", [])
        assert first["reply"] == "Which city are you starting from?"
        second = await ask("Raipur", first["conversation"])
        assert second["reply"] == "What date would you like to start?"
        third = await ask("20 October 2026", second["conversation"])
        assert third["trip_plan"]["kind"] == "destination_trip"
        assert third["trip_plan"]["details"]["source"] == "Raipur"
        assert third["trip_plan"]["details"]["travelers"] == 1
        assert third["trip_plan"]["details"]["preference"] == "comfort"
        assert len(third["trip_plan"]["itinerary"]) == third["trip_plan"]["details"]["nights"] + 1

    import asyncio

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("text", "theme", "month"),
    [
        ("hills in November under 20000 from Raipur", "hills", 11),
        ("Plan a trip to Leh from Delhi starting 15 January 2027", None, 1),
    ],
)
def test_theme_suggestions_and_avoid_season_warnings(text, theme, month):
    plan = build_destination_trip(
        extract_destination_request(text, today=date(2026, 10, 19)),
        text,
    )
    if theme:
        assert plan["kind"] == "destination_suggestions"
        assert len(plan["suggestions"]) == 3
        assert all(item["estimated_total"] <= 20000 for item in plan["suggestions"])
    else:
        assert plan["season_status"] == "avoid"
        assert plan["season_warning"]["month"] == "January"
        assert plan["season_alternatives"]
