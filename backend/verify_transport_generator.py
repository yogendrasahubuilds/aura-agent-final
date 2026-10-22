"""Verify seeded flight, train, and bus mock searches against the city config."""
from datetime import date, datetime, timedelta
import itertools
import re

from generator import TRANSPORT_CITIES, haversine_km
from tools import bus_search, flight_search, train_search

SEARCH_DATE = "2026-11-15"
SAMPLE_ROUTES = [
    ("Raipur", "Delhi"),
    ("Bhilai", "Mumbai"),
    ("Raipur", "Goa"),
    ("Agra", "Delhi"),
    ("Delhi", "Mumbai"),
    ("Mumbai", "Pune"),
    ("Bengaluru", "Chennai"),
    ("Kolkata", "Guwahati"),
    ("Goa", "Kochi"),
    ("Raipur", "Bhilai"),
]
MODES = {
    "Flights": flight_search,
    "Trains": train_search,
    "Buses": bus_search,
}


def _duration_minutes(value: str) -> int:
    match = re.fullmatch(r"(?:(\d+)h)?\s*(?:(\d+)m)?", value.strip())
    if not match or not any(match.groups()):
        raise AssertionError(f"Invalid duration format: {value!r}")
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def _assert_unique_and_chronological(mode: str, route: tuple[str, str], options: list[dict], seen_ids: set[str]) -> None:
    route_ids = [option["id"] for option in options]
    if len(route_ids) != len(set(route_ids)):
        raise AssertionError(f"Duplicate {mode} option IDs for {route[0]}->{route[1]}")
    for option in options:
        if option["id"] in seen_ids:
            raise AssertionError(f"Duplicate {mode} option ID across routes: {option['id']}")
        seen_ids.add(option["id"])
        departure = datetime.combine(
            date.fromisoformat(option.get("date") or SEARCH_DATE),
            datetime.strptime(option["departure"], "%H:%M").time(),
        )
        arrival_date = option.get("arrival_date")
        expected_arrival = departure + timedelta(minutes=_duration_minutes(option["duration"]))
        arrival = datetime.combine(
            date.fromisoformat(arrival_date) if arrival_date else expected_arrival.date(),
            datetime.strptime(option["arrival"], "%H:%M").time(),
        )
        if arrival <= departure:
            raise AssertionError(f"Arrival is not after departure for {mode} option {option['id']}")
        if arrival != expected_arrival:
            raise AssertionError(
                f"Arrival/duration mismatch for {mode} option {option['id']}: "
                f"expected {expected_arrival.isoformat()}, got {arrival.isoformat()}"
            )


def _check_price_spread(mode: str, route: tuple[str, str], options: list[dict]) -> None:
    if len(options) < 2:
        return
    prices = [option["price"] for option in options]
    if max(prices) < min(prices) * 2.5:
        raise AssertionError(
            f"{mode} price spread below 2.5x for {route[0]}->{route[1]}: "
            f"{min(prices)}..{max(prices)}"
        )


def main() -> None:
    city_names = list(TRANSPORT_CITIES)
    route_counts = {"Flights": 0, "Trains": 0, "Buses": 0}
    seen_ids = {mode: set() for mode in MODES}
    for source, destination in itertools.combinations(city_names, 2):
        source_city = TRANSPORT_CITIES[source]
        destination_city = TRANSPORT_CITIES[destination]
        distance = haversine_km(source, destination)
        if source_city["airport"] and destination_city["airport"] and distance and distance > 300:
            route_counts["Flights"] += 1
        if source_city["railStations"] and destination_city["railStations"]:
            route_counts["Trains"] += 1
        if source_city["busHub"] and destination_city["busHub"] and distance is not None and distance <= 1000:
            route_counts["Buses"] += 1

        for mode, search in MODES.items():
            options = search(source=source, destination=destination, date=SEARCH_DATE)
            allowed = {
                "Flights": bool(source_city["airport"] and destination_city["airport"] and distance and distance > 300),
                "Trains": bool(source_city["railStations"] and destination_city["railStations"]),
                "Buses": bool(source_city["busHub"] and destination_city["busHub"] and distance is not None and distance <= 1000),
            }[mode]
            if bool(options) != allowed:
                raise AssertionError(f"{mode} eligibility mismatch for {source}->{destination}")
            if options and not 6 <= len(options) <= 8:
                raise AssertionError(f"{mode} returned {len(options)} options for eligible route {source}->{destination}")
            if len(options) > 8:
                raise AssertionError(f"{mode} returned more than eight options for {source}->{destination}")
            _assert_unique_and_chronological(mode, (source, destination), options, seen_ids[mode])
            _check_price_spread(mode, (source, destination), options)

    for mode, search in MODES.items():
        first = search(source="Raipur", destination="Delhi", date=SEARCH_DATE)
        refreshed = search(source="Raipur", destination="Delhi", date=SEARCH_DATE)
        if first != refreshed:
            raise AssertionError(f"{mode} results changed on refresh for the same route and date")
        next_day = search(source="Raipur", destination="Delhi", date="2026-11-16")
        first_ids = {option["id"] for option in first if option.get("generated")}
        next_day_ids = {option["id"] for option in next_day if option.get("generated")}
        if first_ids and first_ids == next_day_ids:
            raise AssertionError(f"{mode} generated IDs did not vary with travel date")

    print(f"Valid city-pair route counts (unordered, {len(city_names)} cities):")
    for mode, count in route_counts.items():
        print(f"  {mode}: {count}")

    print(f"\nSample routes for {SEARCH_DATE} (option count; minimum..maximum INR):")
    for source, destination in SAMPLE_ROUTES:
        print(f"\n{source} -> {destination}")
        for mode, search in MODES.items():
            options = search(source=source, destination=destination, date=SEARCH_DATE)
            prices = [option["price"] for option in options]
            price_range = f"Rs {min(prices):,}..Rs {max(prices):,}" if prices else "no options"
            print(f"  {mode}: {len(options)} options; {price_range}")


if __name__ == "__main__":
    main()
