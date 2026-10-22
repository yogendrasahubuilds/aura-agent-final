"""Deterministic destination-aware trip planning over AURA's simulated tool data."""
import math
import re
from datetime import date, datetime, timedelta

from booking_pricing import price_booking
from config.registry import run_registered_tool
from destination_data import (
    DESTINATIONS,
    generateDestinationHotels,
    getTransfers,
    isInSeason,
    listDestinations,
)
from generator import TRANSPORT_CITIES, _GENERATED_CACHE, resolve_city


THEMES = ("beach", "hills", "culture", "spiritual", "adventure", "wildlife", "food", "nature")
TRANSPORT_MODES = ("flight", "train", "bus")
TIER_NAMES = ("Budget", "Comfort", "Premium")


def _normalize(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _start_date(text, today=None):
    today = today or date.today()
    iso = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None
    month_names = "|".join(
        value
        for month in range(1, 13)
        for value in (
            datetime(2000, month, 1).strftime("%B"),
            datetime(2000, month, 1).strftime("%b"),
        )
    )
    month_pattern = re.compile(month_names, re.IGNORECASE)
    match = re.search(rf"\b(\d{{1,2}})\s+({month_names})(?:\s+(20\d{{2}}))?\b", text, re.IGNORECASE)
    if not match:
        match = re.search(rf"\b({month_names})\s+(\d{{1,2}})(?:,?\s+(20\d{{2}}))?\b", text, re.IGNORECASE)
        if match:
            month_number = datetime.strptime(match.group(1)[:3].title(), "%b").month
            day = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else today.year
        else:
            month_only = month_pattern.search(text)
            if not month_only:
                return None
            month_number = datetime.strptime(month_only.group(0)[:3].title(), "%b").month
            year_match = re.search(r"\b(20\d{2})\b", text)
            year = int(year_match.group(1)) if year_match else (
                today.year + (month_number < today.month or (month_number == today.month and today.day > 1))
            )
            day = 1
    else:
        day = int(match.group(1))
        month_number = datetime.strptime(match.group(2)[:3].title(), "%b").month
        year = int(match.group(3)) if match.group(3) else today.year
        try:
            candidate = date(year, month_number, day)
        except ValueError:
            return None
        if match.group(3) is None and candidate < today:
            year += 1
    try:
        candidate = date(year, month_number, day)
    except ValueError:
        return None
    if candidate < today and not re.search(r"\b20\d{2}\b", text):
        candidate = date(year + 1, month_number, day)
    return candidate


def _destination_in_text(text):
    lowered = text.casefold()
    match = None
    for destination in DESTINATIONS:
        names = {destination["name"], destination["id"]}
        if destination["name"] == "Leh-Ladakh":
            names.add("Leh")
        if destination["name"] == "Port Blair (Andaman)":
            names.add("Port Blair")
        if destination["name"] == "Jagdalpur-Chitrakote":
            names.update(("Jagdalpur", "Chitrakote"))
        for name in names:
            if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", lowered, re.IGNORECASE):
                if match is None or len(name) > len(match[0]):
                    match = (name, destination)
    return match[1] if match else None


def _source_in_text(text):
    city_names = sorted(TRANSPORT_CITIES, key=len, reverse=True)
    city_pattern = "|".join(re.escape(city) for city in city_names)
    match = re.search(rf"\bfrom\s+({city_pattern})\b", text, re.IGNORECASE)
    if match:
        return resolve_city(match.group(1))
    return None


def _theme_in_text(text):
    lowered = text.casefold()
    return next((theme for theme in THEMES if re.search(rf"\b{theme}\b", lowered)), None)


def extract_destination_request(text, previous=None, today=None):
    """Extract supported trip details without consulting an LLM."""
    previous = previous or {}
    destination = _destination_in_text(text)
    source = _source_in_text(text)
    travelers = None
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    match = re.search(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
        r"(?:travelers?|people|persons?|friends?|adults?)\b",
        text,
        re.IGNORECASE,
    )
    if match:
        value = match.group(1).casefold()
        travelers = int(value) if value.isdigit() else words[value]
    nights = None
    match = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight)\s+nights?\b", text, re.IGNORECASE)
    if match:
        value = match.group(1).casefold()
        nights = int(value) if value.isdigit() else words[value]
    if nights is None:
        match = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight)\s+days?\b", text, re.IGNORECASE)
        if match:
            value = match.group(1).casefold()
            nights = max(1, (int(value) if value.isdigit() else words[value]) - 1)

    budget_match = re.search(
        r"(?:₹|rs\.?\s*|(?:budget|under|within)\s*(?:of\s*)?(?:₹|rs\.?\s*)?)"
        r"(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )
    preference_match = re.search(r"\b(budget|comfort|premium|luxury)\b", text, re.IGNORECASE)
    preference = preference_match.group(1).casefold() if preference_match else None
    if preference == "luxury":
        preference = "premium"
    details = {
        **previous,
        "source": source or previous.get("source"),
        "destination": destination["name"] if destination else previous.get("destination"),
        "theme": _theme_in_text(text) or previous.get("theme"),
        "start_date": (_start_date(text, today) or previous.get("start_date")),
        "nights": nights or previous.get("nights"),
        "travelers": travelers or previous.get("travelers") or 1,
        "budget": int(budget_match.group(1).replace(",", "")) if budget_match else previous.get("budget"),
        "preference": preference or previous.get("preference") or "comfort",
        "interests": [theme for theme in THEMES if re.search(rf"\b{theme}\b", text, re.IGNORECASE)]
        or previous.get("interests")
        or [],
        "one_way": bool(re.search(r"\b(one[- ]way|one way only)\b", text, re.IGNORECASE))
        or previous.get("one_way", False),
    }
    if details["destination"] and details["nights"] is None:
        details["nights"] = max(
            1,
            int(next(item for item in DESTINATIONS if item["name"] == details["destination"])["suggestedDurationDays"]["ideal"]) - 1,
        )
    return details


def _tool_search(mode, source, destination, travel_date, travelers):
    return run_registered_tool(mode, {
        "source": source,
        "destination": destination,
        "date": travel_date.isoformat(),
        "passengers": travelers,
    }, {}).get("results", [])


def _duration_minutes(option):
    match = re.fullmatch(r"\s*(?:(\d+)h)?\s*(?:(\d+)m)?\s*", str(option.get("duration", "")))
    if not match:
        return 0
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def _duration_label(minutes):
    hours, remainder = divmod(int(minutes), 60)
    return f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"


def _tiered(options, mode):
    if len(options) < 3:
        return []
    ordered = sorted(options, key=lambda option: float(option.get("price", 0)))
    result = []
    for tier, option in zip(TIER_NAMES, (ordered[0], ordered[len(ordered) // 2], ordered[-1])):
        if all(existing["id"] != option["id"] for existing in result):
            result.append({**option, "tier": tier, "intent": mode})
    return result


def _choose_tier(options, preference):
    tier = {"budget": "Budget", "comfort": "Comfort", "premium": "Premium"}.get(preference, "Comfort")
    return next((option for option in options if option["tier"] == tier), options[0] if options else None)


def _explain_transport_options(options, mode, preference, recommended_mode):
    if not options:
        return []
    cheapest = min(option["price"] for option in options)
    return [
        {
            **option,
            "recommended": (
                mode == recommended_mode and option["tier"] == preference.title()
            ),
            "reason": (
                f"Recommended {preference} tier based on the route estimate."
                if mode == recommended_mode and option["tier"] == preference.title()
                else f"Rs {option['price'] - cheapest:,} more per person than this mode's cheapest option."
            ),
        }
        for option in options
    ]


def _transfer_option(destination, gateway, mode, preference):
    gateway_type = {"flight": "airport", "train": "rail", "bus": "rail"}[mode]
    transfers = getTransfers(destination, gateway)
    transfer = next((item for item in transfers if item["gatewayType"] == gateway_type), None)
    if transfer is None:
        transfer = next((item for item in transfers if item["gatewayType"] in ("airport", "rail")), None)
    if not transfer:
        return None
    low, high = transfer["priceINR"]
    estimate = low if preference == "budget" else high if preference == "premium" else round((low + high) / 2)
    return {**transfer, "priceINR": estimate, "mode": transfer["mode"], "bookable": False}


def _hotel_options(destination, start_date, preference, nights, rooms=1):
    hotels = generateDestinationHotels(destination, start_date.month, count=8)
    for option in hotels:
        _GENERATED_CACHE[option["id"]] = {"intent": "hotel", "data": option}
    ordered = sorted(hotels, key=lambda option: option["price_per_night"])
    budget_options = [
        option for option in ordered
        if option["category"] != "Hostel/Budget" or preference == "budget"
    ]
    budget = budget_options[0] if budget_options else ordered[0]
    comfort_options = [option for option in hotels if option["category"] == "3-star"]
    comfort = max(
        comfort_options or budget_options,
        key=lambda option: option["rating"] / max(option["price_per_night"], 1),
    )
    premium_options = [option for option in hotels if option["category"] == "5-star"]
    premium = max(premium_options, key=lambda option: option["price_per_night"])
    picks = []
    for tier, option in zip(TIER_NAMES, (budget, comfort, premium)):
        if all(existing["id"] != option["id"] for existing in picks):
            picks.append({**option, "tier": tier, "recommended": tier == {
                "budget": "Budget", "comfort": "Comfort", "premium": "Premium"
            }.get(preference, "Comfort"), "intent": "hotel"})
    cheapest = min(option["price_per_night"] for option in picks)
    for option in picks:
        difference = option["price_per_night"] - cheapest
        stay_total = option["price_per_night"] * nights * rooms
        option["reason"] = (
            f"Best-value 3-star option at Rs {option['price_per_night']:,} per night "
            f"(Rs {stay_total:,} for {nights} nights across {rooms} room{'s' if rooms != 1 else ''})."
            if option["recommended"] and preference == "comfort"
            else (
                f"Recommended tier at Rs {option['price_per_night']:,} per night "
                f"(Rs {stay_total:,} for {nights} nights across {rooms} room{'s' if rooms != 1 else ''})."
            )
            if option["recommended"]
            else (
                f"Lowest available Budget rate at Rs {option['price_per_night']:,} per night "
                f"(Rs {stay_total:,} for {nights} nights across {rooms} room{'s' if rooms != 1 else ''})."
            )
            if option["tier"] == "Budget" and difference == 0
            else (
                f"Rs {difference:,} more per night than the cheapest "
                f"(Rs {difference * nights * rooms:,} more for {nights} nights "
                f"across {rooms} room{'s' if rooms != 1 else ''})."
            )
        )
    return picks


def _transport_candidates(source, destination, travel_date, return_date, travelers, details):
    city_names = set(TRANSPORT_CITIES)
    is_city = destination["name"] in city_names
    candidates = []
    for mode in TRANSPORT_MODES:
        gateway = destination["name"] if is_city else destination["gateway"][
            "airportCity" if mode == "flight" else "railCity"
        ]
        target = gateway if gateway in city_names else None
        if target is None:
            continue
        outbound = _tool_search(mode, source, target, travel_date, travelers)
        returning = [] if details.get("one_way") else _tool_search(mode, target, source, return_date, travelers)
        if not outbound or (not details.get("one_way") and not returning):
            continue
        outbound_tiers = _tiered(outbound, mode)
        return_tiers = _tiered(returning, mode) if returning else []
        if len(outbound_tiers) != 3 or (not details.get("one_way") and len(return_tiers) != 3):
            continue
        transfer = None if is_city else _transfer_option(destination["name"], target, mode, details["preference"])
        if not is_city and transfer is None:
            continue
        candidates.append({
            "mode": mode,
            "gateway": target,
            "outbound": outbound_tiers,
            "return": return_tiers,
            "transfer": transfer,
        })
    return candidates


def _recommended_transport(candidates, details, destination, hotels, daily_days):
    preference = details["preference"]
    travelers = details["travelers"]
    nights = details["nights"]
    rooms = math.ceil(travelers / 2)
    hotel_option = _choose_tier(hotels, preference)
    daily_per_person = destination["dailyBudgetINR"][preference]
    best = None
    for candidate in candidates:
        outbound = _choose_tier(candidate["outbound"], preference)
        returning = _choose_tier(candidate["return"], preference) if candidate["return"] else None
        transport_group_base = (outbound["price"] + (returning["price"] if returning else 0)) * travelers
        transfer_group = (
            candidate["transfer"]["priceINR"] * (2 if returning else 1)
            if candidate["transfer"] else 0
        )
        stay = hotel_option["price_per_night"] * nights * rooms
        day_weight = max(0, daily_days - 2) + (1.1 if daily_days > 1 else 0.55)
        daily = max(0, daily_per_person - hotel_option["price_per_night"]) * day_weight * travelers
        price_lines = [
            price_booking(candidate["mode"], outbound, travelers),
        ]
        if returning:
            price_lines.append(price_booking(candidate["mode"], returning, travelers))
        price_lines.append(price_booking("hotel", hotel_option, travelers, nights, rooms))
        taxes_fees = sum(
            line["fees"] + line["tax"] for line in price_lines
        )
        total = transport_group_base + transfer_group + stay + daily + taxes_fees
        score = total
        if details.get("budget") is not None:
            score = (0 if total <= details["budget"] else 1_000_000_000) + total
        if best is None or score < best[0]:
            best = (score, candidate, outbound, returning, hotel_option, {
                "transport": transport_group_base,
                "last_mile": transfer_group,
                "stay": stay,
                "daily": daily,
                "taxes_fees": taxes_fees,
                "total": total,
            })
    return best


def _itinerary(destination, start_date, nights, travelers, preference, interests, hotel_rate):
    days = nights + 1
    attractions = destination["attractions"]
    requested = set(interests or [])
    chosen = [
        attraction for attraction in attractions
        if not requested or any(tag in requested for tag in destination["themes"])
    ] or attractions
    result = []
    cursor = 0
    for day in range(1, days + 1):
        travel = day in (1, days)
        count = 1 if travel else 2
        activities = []
        for index in range(count):
            attraction = chosen[cursor % len(chosen)]
            cursor += 1
            activities.append({
                **attraction,
                "time": ("14:00" if day == 1 else "09:00") if index == 0 else "14:00",
                "approximate": True,
            })
        result.append({
            "day": day,
            "date": (start_date + timedelta(days=day - 1)).isoformat(),
            "travel_day": travel,
            "activities": activities,
            "daily_estimate": round(
                max(0, destination["dailyBudgetINR"][preference] - hotel_rate)
                * travelers
                * (0.55 if travel else 1),
                2,
            ),
            "daily_estimate_note": "Approximate food and local transport estimate; simulated.",
        })
    return result


def _estimated_alternative(destination, source, start_date, nights, travelers, preference):
    details = {
        "source": source, "destination": destination["name"], "start_date": start_date.isoformat(),
        "nights": nights, "travelers": travelers, "preference": preference, "budget": None, "one_way": False,
    }
    hotels = _hotel_options(
        destination["name"], start_date, preference, nights, math.ceil(travelers / 2)
    )
    candidates = _transport_candidates(
        source, destination, start_date, start_date + timedelta(days=nights), travelers, details
    )
    if not hotels:
        return None
    selected = _recommended_transport(candidates, details, destination, hotels, nights + 1) if candidates else None
    if selected:
        duration_minutes = _duration_minutes(selected[2]) if selected[2] else 0
        if selected[3]:
            duration_minutes += _duration_minutes(selected[3])
        if selected[1]["transfer"]:
            duration_minutes += round(selected[1]["transfer"]["durationHours"] * 60) * (2 if selected[3] else 1)
        return {"total": round(selected[5]["total"]), "travel_time_minutes": duration_minutes}
    hotel = _choose_tier(hotels, preference)
    daily_per_person = destination["dailyBudgetINR"][preference]
    stay = hotel["price_per_night"] * nights * math.ceil(travelers / 2)
    day_weight = max(0, nights - 1) + (1.1 if nights >= 1 else 0.55)
    daily = max(0, daily_per_person - hotel["price_per_night"]) * day_weight * travelers
    return {"total": round(stay + daily), "travel_time_minutes": 0}


def build_destination_trip(details, request_text=""):
    """Build a full deterministic plan, suggestions, or one required-field question."""
    start_date = _start_date(str(details.get("start_date") or ""))
    destination_name = details.get("destination")
    destination = next((item for item in DESTINATIONS if item["name"] == destination_name), None)
    theme = details.get("theme") or _theme_in_text(request_text)
    source = resolve_city(details.get("source")) if details.get("source") else None
    if not destination and not theme:
        return {"question": "Which destination or trip theme should I plan?"}
    if not source:
        return {"question": "Which city are you starting from?"}
    if not start_date:
        return {"question": "What date would you like to start?"}

    preference = details.get("preference") if details.get("preference") in ("budget", "comfort", "premium") else "comfort"
    travelers = max(1, int(details.get("travelers") or 1))
    if destination is None:
        month = start_date.month
        budget = details.get("budget")
        matches = listDestinations(theme=theme, month=month)
        suggestions = []
        for candidate in matches:
            duration = int(details.get("nights") or max(
                1, candidate["suggestedDurationDays"]["ideal"] - 1
            ))
            estimate = _estimated_alternative(candidate, source, start_date, duration, travelers, preference)
            if estimate is None or (budget is not None and estimate["total"] > budget):
                continue
            suggestions.append({
                "id": candidate["id"],
                "destination": candidate["name"],
                "state": candidate["state"],
                "themes": candidate["themes"],
                "estimated_total": estimate["total"],
                "travel_time_minutes": estimate["travel_time_minutes"],
                "travel_time": _duration_label(estimate["travel_time_minutes"]),
                "gateway": candidate["gateway"],
                "select_message": f"Plan a trip to {candidate['name']} from {source} starting {start_date.isoformat()}",
            })
        suggestions.sort(key=lambda option: option["estimated_total"])
        return {
            "kind": "destination_suggestions",
            "details": {
                **details, "source": source, "start_date": start_date.isoformat(),
                "travelers": travelers, "preference": preference, "theme": theme,
            },
            "sections": ["destination_suggestions"],
            "suggestions": suggestions[:3],
            "season_status": "in_season",
            "budget": budget,
        }

    nights = max(1, int(details.get("nights") or (
        int(destination["suggestedDurationDays"]["ideal"]) - 1
    )))
    if not destination.get("gateway", {}).get("airportCity") or not destination.get("gateway", {}).get("railCity"):
        raise ValueError(f"Destination {destination['name']} has no configured gateway.")
    return_date = start_date + timedelta(days=nights)
    normalized_details = {
        "source": source,
        "destination": destination["name"],
        "destination_id": destination["id"],
        "start_date": start_date.isoformat(),
        "return_date": None if details.get("one_way") else return_date.isoformat(),
        "nights": nights,
        "travelers": travelers,
        "rooms": max(1, math.ceil(travelers / 2)),
        "budget": details.get("budget"),
        "preference": preference,
        "interests": details.get("interests") or destination["themes"],
        "one_way": bool(details.get("one_way")),
    }
    hotels = _hotel_options(
        destination["name"], start_date, preference, nights, normalized_details["rooms"]
    )
    if not hotels:
        raise ValueError(f"No simulated hotels are available for {destination['name']}.")
    candidates = _transport_candidates(
        source, destination, start_date, return_date, travelers, normalized_details
    )
    selected = _recommended_transport(
        candidates, normalized_details, destination, hotels, nights + 1
    ) if candidates else None
    route_legs = []
    transport_options = []
    cost_breakdown = {
        "transport": 0.0, "last_mile": 0.0, "stay": 0.0, "daily": 0.0, "taxes_fees": 0.0,
    }
    if selected:
        _score, candidate, outbound, returning, selected_hotel, costs = selected
        recommended_mode = candidate["mode"]
        transport_options = _explain_transport_options(
            candidate["outbound"], candidate["mode"], preference, recommended_mode
        )
        mode_names = {"flight": "Flight", "train": "Train", "bus": "Bus"}
        route_legs.append({
            "type": "transport", "direction": "outbound", "mode": candidate["mode"],
            "mode_label": mode_names[candidate["mode"]], "from": source,
            "to": candidate["gateway"], "option": outbound,
            "departure": outbound["departure"], "arrival": outbound["arrival"],
            "duration": outbound["duration"], "duration_minutes": _duration_minutes(outbound),
            "price_per_person": outbound["price"], "group_total": outbound["price"] * travelers,
            "bookable": True,
        })
        transfer = candidate["transfer"]
        if transfer:
            route_legs.append({
                "type": "transfer", "direction": "outbound", "mode": transfer["mode"],
                "from": candidate["gateway"], "to": destination["name"],
                "duration_hours": transfer["durationHours"],
                "duration_minutes": round(transfer["durationHours"] * 60),
                "price_per_person": round(transfer["priceINR"] / travelers, 2),
                "group_total": transfer["priceINR"], "bookable": False,
                "estimate_only": True, "distance_km": transfer["distanceKm"],
            })
        if returning:
            if transfer:
                route_legs.append({
                    "type": "transfer", "direction": "return", "mode": transfer["mode"],
                    "from": destination["name"], "to": candidate["gateway"],
                    "duration_hours": transfer["durationHours"],
                    "duration_minutes": round(transfer["durationHours"] * 60),
                    "price_per_person": round(transfer["priceINR"] / travelers, 2),
                    "group_total": transfer["priceINR"], "bookable": False,
                    "estimate_only": True, "distance_km": transfer["distanceKm"],
                })
            route_legs.append({
                "type": "transport", "direction": "return", "mode": candidate["mode"],
                "mode_label": mode_names[candidate["mode"]], "from": candidate["gateway"],
                "to": source, "option": returning, "departure": returning["departure"],
                "arrival": returning["arrival"], "duration": returning["duration"],
                "duration_minutes": _duration_minutes(returning),
                "price_per_person": returning["price"], "group_total": returning["price"] * travelers,
                "bookable": True,
            })
        cost_breakdown = costs
        return_options = _explain_transport_options(
            candidate["return"], candidate["mode"], preference, recommended_mode
        )
    else:
        # A gateway that is also the origin has no bookable long-distance leg;
        # the explicitly configured transfer remains the route leg.
        gateway = destination["gateway"]["railCity"]
        transfer = _transfer_option(destination["name"], gateway, "train", preference)
        if source == gateway and transfer:
            route_legs.append({
                "type": "transfer", "direction": "outbound", "mode": transfer["mode"],
                "from": gateway, "to": destination["name"],
                "duration_hours": transfer["durationHours"],
                "duration_minutes": round(transfer["durationHours"] * 60),
                "price_per_person": round(transfer["priceINR"] / travelers, 2),
                "group_total": transfer["priceINR"], "bookable": False,
                "estimate_only": True, "distance_km": transfer["distanceKm"],
            })
            if not details.get("one_way"):
                route_legs.append({
                    "type": "transfer", "direction": "return", "mode": transfer["mode"],
                    "from": destination["name"], "to": gateway,
                    "duration_hours": transfer["durationHours"],
                    "duration_minutes": round(transfer["durationHours"] * 60),
                    "price_per_person": round(transfer["priceINR"] / travelers, 2),
                    "group_total": transfer["priceINR"], "bookable": False,
                    "estimate_only": True, "distance_km": transfer["distanceKm"],
                })
                cost_breakdown["last_mile"] = transfer["priceINR"] * 2
            else:
                cost_breakdown["last_mile"] = transfer["priceINR"]
        return_options = []
        recommended_mode = None
    if not route_legs:
        return {
            "kind": "destination_trip_unavailable",
            "error": "No route was found using the simulated flight, train, bus, or configured gateway transfers.",
            "nearest_alternative_city": destination["gateway"]["railCity"],
        }

    selected_hotel = _choose_tier(hotels, preference)
    if selected:
        # Ensure hotel cost and booking fees match the selected visible hotel.
        stay_pricing = price_booking("hotel", selected_hotel, travelers, nights, normalized_details["rooms"])
        cost_breakdown["stay"] = selected_hotel["price_per_night"] * nights * normalized_details["rooms"]
        daily_budget = destination["dailyBudgetINR"][preference]
        daily_weight = max(0, nights - 1) + (1.1 if nights >= 1 else 0.55)
        cost_breakdown["daily"] = max(0, daily_budget - selected_hotel["price_per_night"]) * daily_weight * travelers
        cost_breakdown["taxes_fees"] = (
            stay_pricing["fees"] + stay_pricing["tax"]
            + price_booking(candidate["mode"], outbound, travelers)["fees"]
            + price_booking(candidate["mode"], outbound, travelers)["tax"]
        )
        if returning:
            return_pricing = price_booking(candidate["mode"], returning, travelers)
            cost_breakdown["taxes_fees"] += return_pricing["fees"] + return_pricing["tax"]
        if candidate["transfer"]:
            multiplier = 2 if returning else 1
            cost_breakdown["last_mile"] = candidate["transfer"]["priceINR"] * multiplier
        if details.get("one_way"):
            cost_breakdown["transport"] = outbound["price"] * travelers
    else:
        hotel_options = hotels
        stay_pricing = price_booking("hotel", selected_hotel, travelers, nights, normalized_details["rooms"])
        cost_breakdown["stay"] = selected_hotel["price_per_night"] * nights * normalized_details["rooms"]
        cost_breakdown["taxes_fees"] = stay_pricing["fees"] + stay_pricing["tax"]
        daily_budget = destination["dailyBudgetINR"][preference]
        daily_weight = max(0, nights - 1) + (1.1 if nights >= 1 else 0.55)
        cost_breakdown["daily"] = max(0, daily_budget - selected_hotel["price_per_night"]) * daily_weight * travelers
        if not details.get("one_way"):
            cost_breakdown["last_mile"] = route_legs[0]["group_total"] * 2
    cost_breakdown["total"] = round(sum(
        cost_breakdown[key] for key in ("transport", "last_mile", "stay", "daily", "taxes_fees")
    ), 2)

    month = start_date.month
    season_ok = isInSeason(destination["name"], month)
    season_avoided = month in destination["season"]["avoidMonths"]
    season_warning = None
    alternatives = []
    if month in destination["season"]["avoidMonths"]:
        season_warning = {
            "destination": destination["name"],
            "month": start_date.strftime("%B"),
            "reason": destination["season"]["avoidReason"],
        }
        for alternative in listDestinations(theme=theme or destination["themes"][0], month=month):
            if alternative["id"] == destination["id"]:
                continue
            estimate = _estimated_alternative(alternative, source, start_date, nights, travelers, preference)
            if estimate is not None:
                alternatives.append({
                    "id": alternative["id"], "destination": alternative["name"],
                    "estimated_total": estimate["total"],
                    "travel_time_minutes": estimate["travel_time_minutes"],
                    "travel_time": _duration_label(estimate["travel_time_minutes"]),
                    "gateway": alternative["gateway"],
                })
            if len(alternatives) == 3:
                break
    itinerary = _itinerary(
        destination, start_date, nights, travelers, preference, normalized_details["interests"],
        selected_hotel["price_per_night"],
    )
    route_duration = sum(leg.get("duration_minutes", 0) for leg in route_legs)
    budget_tier_estimate = _estimated_alternative(
        destination, source, start_date, nights, travelers, "budget"
    )["total"]
    shorter_stay_estimate = (
        _estimated_alternative(destination, source, start_date, nights - 1, travelers, "budget")["total"]
        if nights > 1 else budget_tier_estimate
    )
    min_total = min(cost_breakdown["total"], budget_tier_estimate, shorter_stay_estimate)
    budget_status = None
    if details.get("budget") is not None:
        budget_status = {
            "budget": details["budget"],
            "remaining": round(details["budget"] - cost_breakdown["total"], 2),
            "over_budget": cost_breakdown["total"] > details["budget"],
            "minimum_needed": round(min_total, 2) if cost_breakdown["total"] > details["budget"] else None,
            "cheaper_changes": (
                ["Switch to Budget transport and hotel tiers", "Consider a shorter stay", "Compare an in-season alternative"]
                if cost_breakdown["total"] > details["budget"] else []
            ),
        }
    output_options = {
        "trip_route": transport_options,
        "return": return_options,
        "hotel": hotels,
    }
    for option_set in candidates:
        mode_recommended = option_set["mode"] == recommended_mode
        output_options[option_set["mode"]] = _explain_transport_options(
            option_set["outbound"], option_set["mode"], preference, recommended_mode
        )
        output_options[f"{option_set['mode']}_return"] = _explain_transport_options(
            option_set["return"], option_set["mode"], preference, recommended_mode
        )
    return {
        "kind": "destination_trip",
        "details": normalized_details,
        "destination": destination,
        "sections": ["trip_route", "hotel", "itinerary", "cost_breakdown"],
        "transport_mode": recommended_mode,
        "options": output_options,
        "hotel_count": len(hotels),
        "recommended_hotel_id": selected_hotel["id"],
        "route_legs": route_legs,
        "route_duration_minutes": route_duration,
        "itinerary": itinerary,
        "season_status": "avoid" if season_avoided else "in_season" if season_ok else "shoulder",
        "season_warning": season_warning,
        "season_alternatives": alternatives,
        "cost_breakdown": cost_breakdown,
        "budget_status": budget_status,
        "taxes_fees": cost_breakdown["taxes_fees"],
        "grand_total": cost_breakdown["total"],
        "per_person": round(cost_breakdown["total"] / travelers, 2),
        "rooms": normalized_details["rooms"],
        "selected_defaults": {
            "transport": next((item for item in transport_options if item.get("recommended")), None),
            "return": next((item for item in return_options if item.get("recommended")), None),
            "hotel": selected_hotel,
        },
        "explanation": {
            "transport": f"Recommended {preference} tier using {recommended_mode} tool results." if recommended_mode else "Gateway transfer only; no bookable transport leg is available.",
            "hotel": f"Recommended {selected_hotel['category']} option at Rs {selected_hotel['price_per_night']:,} per night.",
        },
        "simulated": True,
    }
