import asyncio

import pytest

import agent
from config.registry import (
    MissingToolParameters,
    TOOL_REGISTRY,
    resolve_parameters,
    run_registered_tool,
    validate_plan,
)
from booking import create_mock_booking
from tools import get_option_by_id
import server

CHECKOUT_DATA = {
    "passengers": [
        {"name": "Traveler", "age": 30, "gender": "Prefer not to say"},
        {"name": "Traveler 2", "age": 30, "gender": "Prefer not to say"},
        {"name": "Traveler 3", "age": 30, "gender": "Prefer not to say"},
        {"name": "Traveler 4", "age": 30, "gender": "Prefer not to say"},
    ],
    "contact": {"email": "test@example.com", "phone": "9876543210"},
    "payment_method": "UPI",
}


class MemoryCollection:
    def __init__(self):
        self.documents = []

    async def insert_one(self, document):
        self.documents.append(dict(document))

    async def update_one(self, query, update, upsert=False):
        document = next(
            (item for item in self.documents if all(item.get(k) == v for k, v in query.items())),
            None,
        )
        if document is None and upsert:
            document = dict(query)
            self.documents.append(document)
        if document:
            document.update(update.get("$set", {}))

    async def find_one(self, query, _projection=None):
        return next(
            (dict(item) for item in self.documents if all(item.get(k) == v for k, v in query.items())),
            None,
        )


class MemoryDatabase:
    def __init__(self):
        self.conversations = MemoryCollection()
        self.agent_runs = MemoryCollection()
        self.users = MemoryCollection()
        self.bookings = MemoryCollection()
        self.execution_logs = MemoryCollection()


def test_signup_login_and_bearer_authentication(monkeypatch):
    database = MemoryDatabase()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "AUTH_ENABLED", True)
    monkeypatch.setenv("JWT_SECRET", "test-only-secret-with-32-bytes!!")

    async def exercise():
        created = await server.signup(
            server.SignupRequest(name="  AURA User ", email="USER@example.com", password="secret1")
        )
        stored = database.users.documents[0]
        assert stored["email"] == "user@example.com"
        assert stored["name"] == "AURA User"
        assert stored["password_hash"] != "secret1"
        assert "password" not in created["user"]

        logged_in = await server.login(
            server.LoginRequest(email="user@example.com", password="secret1")
        )
        authenticated = await server.get_current_user(f"Bearer {logged_in['access_token']}")
        assert authenticated == created["user"]

        with pytest.raises(server.HTTPException) as duplicate:
            await server.signup(
                server.SignupRequest(name="Another", email="user@example.com", password="secret2")
            )
        assert duplicate.value.status_code == 409

        with pytest.raises(server.HTTPException) as invalid:
            await server.get_current_user("Bearer invalid")
        assert invalid.value.status_code == 401

    asyncio.run(exercise())


def test_disabled_auth_uses_guest_and_in_memory_database(monkeypatch):
    monkeypatch.setattr(server, "AUTH_ENABLED", False)

    async def exercise():
        assert await server.get_current_user() == server.DEFAULT_USER
        assert await server.auth_me(server.DEFAULT_USER) == {
            **server.DEFAULT_USER,
            "auth_enabled": False,
        }
        with pytest.raises(server.HTTPException, match="Authentication is disabled"):
            await server.signup(
                server.SignupRequest(name="Guest", email="guest@example.com", password="secret1")
            )
        with pytest.raises(server.HTTPException, match="Authentication is disabled"):
            await server.login(server.LoginRequest(email="guest@example.com", password="secret1"))

        memory = server.InMemoryDatabase()
        await memory.agent_runs.insert_one({
            "run_id": "run-1",
            "user_id": "default-user",
            "created_at": "2026-10-18T00:00:00+00:00",
            "steps": [{"status": "pending"}],
        })
        result = await memory.agent_runs.update_one(
            {"run_id": "run-1", "steps.0.status": "pending"},
            {"$set": {"steps.0.status": "done"}},
        )
        assert result.matched_count == 1
        history = await memory.agent_runs.find(
            {"user_id": "default-user"}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        assert history[0]["steps"][0]["status"] == "done"

    asyncio.run(exercise())

    class OfflineClient:
        class admin:
            @staticmethod
            async def command(_command):
                raise ConnectionError("MongoDB unavailable")

    monkeypatch.setattr(server, "db", MemoryDatabase())
    monkeypatch.setattr(server, "using_memory_fallback", False)
    monkeypatch.setattr(server, "client", OfflineClient())
    asyncio.run(server.ensure_user_email_index())
    assert server.using_memory_fallback is True
    assert isinstance(server.db, server.InMemoryDatabase)


def test_registry_contains_only_expected_mock_tools():
    assert set(TOOL_REGISTRY) == {
        "flight",
        "train",
        "bus",
        "hotel",
        "movie",
        "cricket",
        "concert",
        "local_transport",
        "budget_optimizer",
        "trip_planner",
    }
    assert all(callable(entry["handler"]) for entry in TOOL_REGISTRY.values())


def test_shared_option_explanations_use_computed_prices_and_durations():
    raw_options = [
        {"id": "cheap", "price": 1000, "duration": "5h"},
        {"id": "value", "price": 1400, "duration": "3h"},
        {"id": "fast", "price": 1800, "duration": "2h"},
    ]
    annotated = server._annotate_tool_result(
        "flight", {"results": raw_options}
    )
    options = annotated["results"]
    tradeoff = annotated["tradeoff"]
    assert sum(option["recommended"] for option in options) == 1
    assert next(option for option in options if option["recommended"])["id"] == "value"
    assert "Rs 400 more than cheapest" in next(
        option["reason"] for option in options if option["recommended"]
    )
    assert "3h 0m" in tradeoff
    assert all(len(option["reason"].split()) <= 12 for option in options)

    within_budget, _ = server._explain_options(
        [{"id": "budget", "price": 1200}, {"id": "costly", "price": 2400}],
        "flight",
        budget=1500,
    )
    assert sum(option["recommended"] for option in within_budget) == 1
    assert next(option for option in within_budget if option["recommended"])["id"] == "budget"
    assert "Rs 300 left" in next(
        option["reason"] for option in within_budget if option["recommended"]
    )


def test_unknown_tools_are_rejected():
    with pytest.raises(ValueError, match="not in AURA's allow-list"):
        validate_plan([{"tool": "shell", "parameters": {}}])


def test_missing_required_parameters_are_reported():
    with pytest.raises(MissingToolParameters) as exc:
        validate_plan([{"tool": "flight", "parameters": {"source": "Raipur"}}])
    assert exc.value.parameter == "destination"


def test_hotel_reuses_a_prior_flight_date():
    steps = validate_plan([
        {
            "tool": "flight",
            "parameters": {
                "source": "Raipur",
                "destination": "Goa",
                "date": "2026-11-12",
            },
        },
        {"tool": "hotel", "parameters": {"city": "Goa"}},
    ])
    assert steps[1]["parameters"]["check_in"] == "$previous.date"
    resolved = resolve_parameters(
        steps[1]["parameters"],
        {"date": "2026-11-12", "selected_flight": {"date": "2026-11-12"}},
    )
    assert resolved["check_in"] == "2026-11-12"


def test_mock_tools_return_simulated_outputs():
    result = run_registered_tool(
        "train",
        {"source": "Raipur", "destination": "Goa", "date": "2026-11-12"},
        {},
    )
    assert result["simulated"] is True
    assert result["results"]


def test_non_scalar_parameters_are_rejected():
    with pytest.raises(ValueError, match="scalar value"):
        validate_plan([
            {"tool": "movie", "parameters": {"city": ["Bhilai"], "date": "2026-11-12"}}
        ])


def test_trip_planner_extracts_destination_source_nights_and_start_date(monkeypatch):
    async def no_llm(_text, _tool):
        return None

    monkeypatch.setattr(agent, "_llm_task_plan", no_llm)
    plan = asyncio.run(agent.create_task_plan(
        "Plan a trip to Goa for 3 nights from Delhi starting 20 October",
        "trip_planner",
    ))
    parameters = plan["steps"][0]["parameters"]
    assert parameters["destination"] == "Goa"
    assert parameters["source"] == "Delhi"
    assert parameters["nights"] == 3
    assert parameters["start_date"] == "2026-10-20"


@pytest.mark.parametrize(
    "text,travelers",
    [
        ("Plan for 4 friends", 4),
        ("we are 5", 5),
        ("family of 4", 4),
        ("Plan with three people", 3),
    ],
)
def test_trip_details_extract_group_sizes(text, travelers):
    assert agent.extract_trip_details(text)["travelers"] == travelers


def test_conversation_defaults_unspecified_group_size_without_an_extra_question(monkeypatch):
    async def no_llm(*_args):
        return None

    monkeypatch.setattr(server, "db", MemoryDatabase())
    monkeypatch.setattr(server, "conversational_turn", no_llm)
    monkeypatch.setattr(server, "summarize_trip_results", no_llm)

    async def exercise():
        first = await server.chat(server.ChatRequest(
            message="Plan a trip to Goa from Delhi starting 20 October with my friends and I",
            user_id="group-trip-test",
            mode="conversation",
        ))
        assert first["trip_plan"]["details"]["travelers"] == 1
        assert first["trip_plan"]["kind"] == "destination_trip"

    asyncio.run(exercise())


def test_hotel_confirmation_calculates_shared_rooms():
    option = get_option_by_id("hotel", "HTL002")
    assert option

    async def exercise():
        response = await server.confirm(server.ConfirmRequest(
            intent="hotel",
            option_id="HTL002",
            quantity=4,
            rooms=2,
            nights=3,
        ))
        assert response["quantity"] == 4
        assert response["rooms"] == 2
        assert response["amount"]["subtotal"] == option["price_per_night"] * 2 * 3

    asyncio.run(exercise())


def test_hotel_booking_keeps_guest_count_and_room_count(monkeypatch):
    database = MemoryDatabase()
    monkeypatch.setattr(server, "db", database)
    option = get_option_by_id("hotel", "HTL002")
    assert option

    async def exercise():
        booking = await server.book(
            server.BookRequest(
                intent="hotel",
                option_id="HTL002",
                quantity=4,
                rooms=2,
                nights=3,
                confirmed=True,
                **CHECKOUT_DATA,
            ),
            server.DEFAULT_USER,
        )
        assert booking["quantity"] == 4
        assert booking["extra"]["rooms"] == 2
        assert booking["amount"]["subtotal"] == option["price_per_night"] * 2 * 3

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "travelers,budget",
    [
        (1, None),
        (4, 50000),
    ],
)
def test_trip_option_confirmation_and_booking_after_selection(monkeypatch, travelers, budget):
    async def no_llm(*_args):
        return None

    database = MemoryDatabase()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "conversational_turn", no_llm)
    monkeypatch.setattr(server, "summarize_trip_results", no_llm)

    async def exercise():
        budget_text = f" with budget Rs {budget}" if budget is not None else ""
        group_text = f"for {travelers} friends" if travelers > 1 else "for 1 traveler"
        response = await server.chat(server.ChatRequest(
            message=(
                f"Plan a 3 night trip to Goa from Delhi starting 20 October 2026 "
                f"{group_text}{budget_text}"
            ),
            user_id=f"select-booking-{travelers}-{budget}",
            mode="conversation",
        ))
        plan = response["trip_plan"]
        assert plan["details"]["travelers"] == travelers
        assert plan["details"]["budget"] == budget
        options = plan["options"]["trip_route"]
        assert sum(option["recommended"] for option in options) == 1
        selected = next(option for option in options if option["recommended"])
        transport_mode = plan["transport_mode"]
        payload = {
            "intent": transport_mode,
            "option_id": selected["id"],
            "quantity": travelers,
            "nights": 1,
            "rooms": 1,
        }
        preview = await server.confirm(
            server.ConfirmRequest.model_validate(payload)
        )
        assert preview["amount"]["subtotal"] == preview["option"]["price"] * travelers
        booking = await server.book(
            server.BookRequest(
                **payload,
                user_id=f"select-booking-{travelers}-{budget}",
                confirmed=True,
                **{
                    **CHECKOUT_DATA,
                    "passengers": CHECKOUT_DATA["passengers"][:travelers],
                },
            ),
            {"id": f"select-booking-{travelers}-{budget}"},
        )
        assert booking["quantity"] == travelers
        assert booking["amount"] == preview["amount"]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "tool,parameters,expected_count",
    [
        ("train", {"source": "Delhi", "destination": "Agra", "date": "2026-10-18"}, (6, 8)),
        ("bus", {"source": "Delhi", "destination": "Agra", "date": "2026-10-18"}, (6, 8)),
        ("cricket", {"city": "Mumbai", "date": "2026-10-20"}, 6),
        ("concert", {"city": "Mumbai", "date": "2026-10-20"}, 3),
        ("hotel", {"city": "Goa", "check_in": "2026-10-20"}, 10),
    ],
)
def test_booking_search_tools_return_mock_options(tool, parameters, expected_count):
    result = run_registered_tool(tool, parameters, {})
    assert result["simulated"] is True
    if isinstance(expected_count, tuple):
        assert expected_count[0] <= len(result["results"]) <= expected_count[1]
    else:
        assert len(result["results"]) == expected_count


@pytest.mark.parametrize(
    "intent,option_id,prefix",
    [
        ("train", "TRN001", "AURA-TRN-"),
        ("bus", "BUS001", "AURA-BUS-"),
        ("cricket", "CRK001", "AURA-CRK-"),
        ("concert", "CON001", "AURA-CON-"),
        ("hotel", "HTL001", "AURA-HTL-"),
    ],
)
def test_mock_option_lookup_and_booking_ids(intent, option_id, prefix):
    option = get_option_by_id(intent, option_id)
    assert option is not None
    booking = create_mock_booking(
        intent,
        option,
        2,
        {"subtotal": 100, "tax": 18, "total": 118, "currency": "INR"},
        {},
    )
    assert booking["booking_id"].startswith(prefix)
    assert len(booking["booking_id"].rsplit("-", 1)[-1]) == 5


def test_trip_plan_is_ordered_and_feature_tool_is_forced(monkeypatch):
    async def no_llm(_text, _tool):
        return None

    monkeypatch.setattr(agent, "_llm_task_plan", no_llm)
    plan = asyncio.run(
        agent.create_task_plan(
            "Plan a Goa trip from Raipur, flight and hotel on 12 November 2026"
        )
    )
    assert [step["tool"] for step in plan["steps"]] == [
        "budget_optimizer",
        "flight",
        "hotel",
    ]

    feature = asyncio.run(agent.create_task_plan("anything", "train"))
    assert feature["intents"] == ["train"]
    assert [step["tool"] for step in feature["steps"]] == ["train"]


def test_conversation_asks_only_for_required_fields_and_defaults_optional_details(monkeypatch):
    async def no_llm(*_args):
        return None

    database = MemoryDatabase()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "conversational_turn", no_llm)
    monkeypatch.setattr(server, "summarize_trip_results", no_llm)

    async def run_turn(conversation, message):
        return await server.chat(
            server.ChatRequest(
                message=message,
                user_id="trip-chat-test",
                mode="conversation",
                conversation=conversation,
            )
        )

    async def exercise():
        conversation = []
        for message, expected in (
            ("Plan a trip to Goa", "starting from"),
            ("Delhi", "start"),
        ):
            response = await run_turn(conversation, message)
            assert expected in response["reply"].lower()
            conversation = response["conversation"]

        response = await run_turn(conversation, "20 October")
        assert response["ready_to_book"] is True
        details = response["trip_plan"]["details"]
        assert details["source"] == "Delhi"
        assert details["destination"] == "Goa"
        assert details["start_date"] == "2026-10-20"
        assert details["nights"] == 4
        assert details["travelers"] == 1
        assert details["budget"] is None
        assert details["preference"] == "comfort"
        assert details["interests"] == ["beach", "culture", "food", "nature"]
        assert len(response["trip_plan"]["itinerary"]) == 5
        assert "trip_route" in response["trip_plan"]["sections"]
        assert "hotel" in response["trip_plan"]["sections"]
        assert response["trip_plan"]["options"]["trip_route"]
        assert response["trip_plan"]["options"]["hotel"]
        assert sum(
            option["recommended"]
            for option in response["trip_plan"]["options"]["trip_route"]
        ) == 1
        assert all(
            "per night" in option["reason"] and "for 4 nights" in option["reason"]
            for option in response["trip_plan"]["options"]["hotel"]
        )
        why = await run_turn(response["conversation"], "Why this option?")
        assert why["explanation_only"] is True
        flight_reason = next(
            option["reason"]
            for option in response["trip_plan"]["options"]["trip_route"]
            if option["recommended"]
        )
        assert flight_reason in why["reply"]
        assert response["steps"][-1]["tool"] == "trip_planner"
        assert database.agent_runs.documents[0]["status"] == "pending_approval"

        cheaper = await run_turn(response["conversation"], "Make it cheaper")
        assert cheaper["trip_plan"]["details"]["preference"] == "budget"

        extended = await run_turn(cheaper["conversation"], "Add one more night")
        assert extended["trip_plan"]["details"]["nights"] == 5
        assert len(extended["trip_plan"]["itinerary"]) == 6

    asyncio.run(exercise())


def test_event_travel_plan_uses_registry_options_and_only_asks_for_origin(monkeypatch):
    async def no_llm(*_args):
        return None

    database = MemoryDatabase()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "conversational_turn", no_llm)
    monkeypatch.setattr(server, "summarize_trip_results", no_llm)

    async def run_turn(conversation, message, reset=False):
        return await server.chat(
            server.ChatRequest(
                message=message,
                user_id="event-trip-test",
                mode="conversation",
                conversation=conversation,
                reset=reset,
            )
        )

    async def exercise():
        first = await run_turn([], "I want to travel to watch India vs Australia in Mumbai, budget 15000")
        assert first["reply"] == "Which city are you traveling from?"
        assert first["trip_plan"] is None

        response = await run_turn(first["conversation"], "I'm in Delhi")
        plan = response["trip_plan"]
        assert response["ready_to_book"] is True
        assert plan["kind"] == "event_travel"
        assert plan["details"]["source"] == "Delhi"
        assert plan["details"]["event_city"] == "Mumbai"
        assert plan["details"]["event"] == "India vs Australia — T20 International"
        assert plan["details"]["event_date"] == "2026-10-20"
        assert plan["details"]["travelers"] == 1
        assert plan["details"]["budget"] == 15000
        assert [option["tier"] for option in plan["options"]["event"]] == [
            "Budget", "Comfort", "Premium"
        ]
        assert [option["tier"] for option in plan["options"]["hotel"]] == [
            "Budget", "Comfort", "Premium"
        ]
        for section in ("event", "outbound", "hotel"):
            assert sum(option["recommended"] for option in plan["options"][section]) == 1
            if section == "hotel":
                assert all(
                    "per night" in option["reason"]
                    and "for 1 night" in option["reason"]
                    for option in plan["options"][section]
                )
            else:
                assert all(len(option["reason"].split()) <= 12 for option in plan["options"][section])
        visible_returns = [
            option for option in plan["options"]["return"]
            if option["intent"] == plan["defaults"]["outbound"]["intent"]
        ]
        assert sum(option["recommended"] for option in visible_returns) == 1
        assert plan["tradeoffs"]["event"]
        assert plan["tradeoffs"]["outbound"]
        assert plan["defaults"]["outbound"]["intent"] == plan["defaults"]["return"]["intent"]
        assert plan["defaults"]["outbound"]["option"]["travel_date"] == "2026-10-19"
        assert plan["defaults"]["return"]["option"]["travel_date"] == "2026-10-21"
        assert len(response["steps"]) == 9
        assert database.agent_runs.documents[-1]["status"] == "pending_approval"

        missing_origin = await run_turn([], "concert in Bengaluru", reset=True)
        assert missing_origin["reply"] == "Which city are you traveling from?"
        assert missing_origin["trip_plan"] is None

        exact = await run_turn(
            [],
            "I want to watch India vs Australia in Mumbai, I'm in Delhi, for 4 friends, budget 15000",
        )
        assert exact["trip_plan"]["details"]["source"] == "Delhi"
        assert exact["trip_plan"]["details"]["event_city"] == "Mumbai"
        assert exact["trip_plan"]["details"]["budget"] == 15000
        assert exact["trip_plan"]["details"]["travelers"] == 4
        recommended_travel = next(
            option for option in exact["trip_plan"]["options"]["outbound"]
            if option["recommended"]
        )
        preview = await server.confirm(server.ConfirmRequest.model_validate({
            "intent": recommended_travel["intent"],
            "option_id": recommended_travel["id"],
            "quantity": 4,
        }))
        assert preview["quantity"] == 4
        assert preview["amount"]["subtotal"] == preview["option"]["price"] * 4
        why_flight = await run_turn(exact["conversation"], "Why not the flight?")
        flight_reason = next(
            option["reason"]
            for option in exact["trip_plan"]["options"]["outbound"]
            if option["intent"] == "flight"
        )
        assert flight_reason in why_flight["reply"]

        concert = await run_turn(
            [], "concert in Bengaluru from Raipur"
        )
        assert concert["trip_plan"]["kind"] == "event_travel"
        assert concert["trip_plan"]["details"]["source"] == "Raipur"
        assert concert["trip_plan"]["details"]["event_city"] == "Bengaluru"
        assert concert["trip_plan"]["details"]["event_date"] == "2026-11-28"
        assert len(concert["trip_plan"]["options"]["event"]) == 3

        group_question = await run_turn(
            [],
            "concert in Bengaluru from Raipur with my friends and I",
            reset=True,
        )
        assert group_question["reply"] == "How many travelers should I include?"
        group_plan = await run_turn(group_question["conversation"], "we are 5")
        assert group_plan["trip_plan"]["details"]["travelers"] == 5
        assert all(
            step["parameters"].get("passengers", 5) == 5
            for step in group_plan["steps"]
            if step["tool"] in ("flight", "train", "bus")
        )

    asyncio.run(exercise())


def test_hotel_and_local_transport_conversation_sections(monkeypatch):
    async def no_llm(*_args):
        return None

    database = MemoryDatabase()
    monkeypatch.setattr(server, "db", database)
    monkeypatch.setattr(server, "conversational_turn", no_llm)
    monkeypatch.setattr(server, "summarize_trip_results", no_llm)

    async def run_turn(message, conversation=None, reset=False):
        return await server.chat(server.ChatRequest(
            message=message,
            user_id="hotel-local-chat-test",
            mode="conversation",
            conversation=conversation or [],
            reset=reset,
        ))

    async def exercise():
        hotel = await run_turn("Find a hotel in Mumbai, check-in 28 October 2026")
        assert hotel["ready_to_book"] is True
        assert hotel["trip_plan"]["sections"] == ["hotel"]
        assert len(hotel["trip_plan"]["options"]["hotel"]) == 3
        assert sum(option["recommended"] for option in hotel["trip_plan"]["options"]["hotel"]) == 1
        recommended = next(option for option in hotel["trip_plan"]["options"]["hotel"] if option["recommended"])
        assert recommended["category"] == "3-star"
        assert "deluxe" in recommended["room_type"].lower()
        assert all(
            "per night" in option["reason"] and "for 3 nights" in option["reason"]
            for option in hotel["trip_plan"]["options"]["hotel"]
        )
        assert "per night" in hotel["trip_plan"]["tradeoffs"]["hotel"]
        budgeted_options, _ = server._explain_options(
            hotel["trip_plan"]["options"]["hotel"],
            "hotel",
            preference="all",
            budget=5000,
            nights=3,
        )
        assert next(option for option in budgeted_options if option["recommended"])["category"] == "3-star"
        assert "source" not in hotel["trip_plan"]["details"]
        assert "times" not in hotel["reply"]

        local = await run_turn(
            "Show local transport estimates in Mumbai for 3 days",
            reset=True,
        )
        assert local["trip_plan"]["sections"] == ["local_transport"]
        assert "source" not in local["trip_plan"]["details"]
        assert local["trip_plan"]["local_transport_days"] == 3
        assert len(local["trip_plan"]["options"]["local_transport"]) >= 3
        local_modes = {option["mode"] for option in local["trip_plan"]["options"]["local_transport"]}
        assert {"Auto rickshaw", "Taxi", "Metro", "Local bus"} <= local_modes
        assert "per day" in local["trip_plan"]["tradeoffs"]["local_transport"]
        assert all("per day" in option["reason"] for option in local["trip_plan"]["options"]["local_transport"])

        combined = await run_turn(
            "Find a hotel in Mumbai, then show local transport estimates for 3 days; check-in 28 October 2026",
            reset=True,
        )
        assert combined["trip_plan"]["sections"] == ["hotel", "local_transport"]
        assert [step["tool"] for step in combined["steps"]] == ["hotel", "local_transport"]
        assert "3 hotel options and local transport estimates" in combined["reply"]
        assert "times" not in combined["reply"]
        assert combined["trip_plan"]["local_transport_days"] == 3

        date_question = await run_turn("Find a hotel in Mumbai", reset=True)
        assert date_question["reply"] == "What is your hotel check-in date?"
        default_date = await run_turn("yes", date_question["conversation"])
        assert default_date["ready_to_book"] is True
        assert default_date["trip_plan"]["details"]["start_date"]

    asyncio.run(exercise())
