"""Read-only simulated destination lookups and deterministic destination hotel data."""
import copy
import calendar
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Optional


DATA_PATH = Path(__file__).parent / "config" / "destinations.json"
with DATA_PATH.open(encoding="utf-8") as data_file:
    _DATA = json.load(data_file)

DESTINATIONS = _DATA["destinations"]


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _resolve_destination(destination: dict | str | None) -> Optional[dict]:
    if isinstance(destination, dict):
        destination_id = destination.get("id")
        name = destination.get("name")
        return next(
            (
                item for item in DESTINATIONS
                if item["id"] == destination_id or (
                    name and _normalize_name(item["name"]) == _normalize_name(name)
                )
            ),
            None,
        )
    if not isinstance(destination, str):
        return None
    normalized = _normalize_name(destination)
    return next(
        (
            item for item in DESTINATIONS
            if normalized in (_normalize_name(item["id"]), _normalize_name(item["name"]))
        ),
        None,
    )


def _month_number(month: int | str | None) -> Optional[int]:
    if isinstance(month, int) and 1 <= month <= 12:
        return month
    if isinstance(month, str):
        value = month.strip().casefold()
        if value.isdigit() and 1 <= int(value) <= 12:
            return int(value)
        for number in range(1, 13):
            if value in (calendar.month_name[number].casefold(), calendar.month_abbr[number].casefold()):
                return number
    return None


def getDestination(name_or_id: str) -> Optional[dict]:
    """Return a copy of the matching destination by display name or stable ID."""
    destination = _resolve_destination(name_or_id)
    return copy.deepcopy(destination) if destination else None


def listDestinations(
    theme: str | None = None,
    month: int | str | None = None,
    max_daily_budget: int | float | None = None,
) -> list[dict]:
    """Filter by theme, best-season month, or any daily budget tier within a cap."""
    month_value = _month_number(month)
    if month is not None and month_value is None:
        return []
    theme_value = theme.casefold().strip() if theme else None
    return [
        copy.deepcopy(destination)
        for destination in DESTINATIONS
        if (theme_value is None or theme_value in destination["themes"])
        and (
            month_value is None
            or isInSeason(destination, month_value)
        )
        and (
            max_daily_budget is None
            or min(destination["dailyBudgetINR"].values()) <= max_daily_budget
        )
    ]


def getGateway(destination: str | dict, mode: str) -> Optional[str]:
    """Return the configured listed-city gateway for airport or rail access."""
    item = _resolve_destination(destination)
    if not item:
        return None
    mode_value = mode.casefold().strip()
    gateway_key = (
        "airportCity" if mode_value in {"air", "airport", "flight"}
        else "railCity" if mode_value in {"rail", "train", "railway"}
        else None
    )
    if gateway_key is None:
        raise ValueError("mode must be airport/air/flight or rail/train/railway")
    return item["gateway"][gateway_key]


def getTransfers(destination: str | dict, gatewayCity: str) -> list[dict]:
    """Return simulated estimate-only transfer entries from a listed gateway city."""
    item = _resolve_destination(destination)
    if not item or not gatewayCity:
        return []
    city_value = _normalize_name(gatewayCity)
    return [
        copy.deepcopy(transfer)
        for transfer in item["transfers"]
        if _normalize_name(transfer["gatewayCity"]) == city_value
    ]


def isInSeason(destination: str | dict, month: int | str) -> bool:
    """Return whether the month is recommended and not listed as an avoid month."""
    item = _resolve_destination(destination)
    month_value = _month_number(month)
    return bool(
        item
        and month_value
        and month_value in item["season"]["bestMonths"]
        and month_value not in item["season"]["avoidMonths"]
    )


_HOTEL_CATEGORIES = (
    ("Hostel/Budget", 600, 1200, ("Dorm Bed", "Basic Room"), 0),
    ("2-star", 1200, 2500, ("Standard Room", "Standard Twin Room"), 2),
    ("3-star", 2500, 4500, ("Deluxe Room", "Deluxe Twin Room"), 3),
    ("4-star", 4500, 8000, ("Superior Room", "Club Room"), 4),
    ("5-star", 8000, 20000, ("Suite", "Villa"), 5),
)
_HOTEL_TEMPLATES = {
    "Hostel/Budget": ("{locality} Hostel", "{locality} Budget Stay"),
    "2-star": ("{locality} Standard Inn", "{locality} City Rooms"),
    "3-star": ("{locality} Deluxe Stay", "{locality} Comfort Lodge"),
    "4-star": ("{locality} Superior Residence", "{locality} Club Stay"),
    "5-star": ("{locality} Signature Suites", "{locality} Grand Suites"),
}
_HOTEL_LOCALITIES = {
    "Goa": ("Calangute", "Fontainhas"),
    "Jaipur": ("Amber Road", "Civil Lines"),
    "Udaipur": ("Lake Pichola", "Fateh Sagar"),
    "Jodhpur": ("Clock Tower", "Ratanada"),
    "Jaisalmer": ("Fort Road", "Sam Dunes"),
    "Pushkar": ("Brahma Temple Road", "Lake Ghat"),
    "Agra": ("Agra Old City", "Fatehabad Road"),
    "Varanasi": ("Assi Ghat", "Godowlia"),
    "Rishikesh": ("Tapovan", "Laxman Jhula Road"),
    "Haridwar": ("Har Ki Pauri", "Bhoopatwala"),
    "Mussoorie": ("Landour", "Library Chowk"),
    "Nainital": ("Mallital", "Tallital"),
    "Manali": ("Old Manali", "Log Huts"),
    "Shimla": ("Mall Road", "Chhota Shimla"),
    "Amritsar": ("Golden Temple Road", "Lawrence Road"),
    "Leh-Ladakh": ("Leh Bazaar", "Changspa"),
    "Srinagar": ("Dal Lake", "Raj Bagh"),
    "Darjeeling": ("Chowrasta", "Gandhi Road"),
    "Gangtok": ("MG Marg", "Tadong"),
    "Munnar": ("Tea Museum Road", "Chithirapuram"),
    "Alleppey": ("Beach Road", "Finishing Point"),
    "Kochi": ("Fort Kochi", "Marine Drive"),
    "Ooty": ("Charing Cross", "Botanical Road"),
    "Mysuru": ("Palace Road", "Vijayanagar"),
    "Hampi": ("Virupaksha Bazaar", "Kampli Road"),
    "Coorg": ("Madikeri", "Kushalnagar"),
    "Pondicherry": ("White Town", "Auroville Road"),
    "Port Blair (Andaman)": ("Aberdeen Bazaar", "Corbyn's Cove"),
    "Lonavala-Mahabaleshwar": ("Lonavala Market", "Mahabaleshwar Town"),
    "Jagdalpur-Chitrakote": ("Jagdalpur Market", "Chitrakote Road"),
    "Khajuraho": ("Temple Road", "Western Group Road"),
}
_AMENITIES = (
    "Free WiFi", "Breakfast included", "Restaurant", "Parking", "Air conditioning",
    "Garden", "Room service", "Swimming pool", "Tea service", "Local transfers",
)


def generateDestinationHotels(
    destination: str | dict,
    month: int | str | None = None,
    count: int = 8,
) -> list[dict]:
    """Generate 6-8 stable simulated hotel options in the existing hotel field format."""
    item = _resolve_destination(destination)
    if not item:
        return []
    count = min(8, max(6, int(count)))
    month_value = _month_number(month)
    peak_multiplier = (
        item["peakMultiplier"]
        if month_value in item["peakMonths"]
        else 1.0
    )
    seed = int(hashlib.sha256(item["id"].encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    quantities = [1] * len(_HOTEL_CATEGORIES)
    for index in range(count - len(_HOTEL_CATEGORIES)):
        quantities[index % 3] += 1
    category_rows = [
        (category, low, high, room_types, star_rating, variant)
        for (category, low, high, room_types, star_rating), quantity in zip(
            _HOTEL_CATEGORIES, quantities
        )
        for variant in range(quantity)
    ]

    localities = _HOTEL_LOCALITIES[item["name"]]
    hotels = []
    for index, (category, low, high, room_types, star_rating, variant) in enumerate(category_rows):
        multiplier = item["hotelPriceMultiplier"] * peak_multiplier
        price = int(round(rng.randint(low, high) * multiplier / 10) * 10)
        locality = localities[variant % len(localities)]
        hotel_seed = f"{item['id']}|{index}".encode()
        hotel_id = f"GHT-{hashlib.sha256(hotel_seed).hexdigest()[:12].upper()}"
        hotels.append({
            "id": hotel_id,
            "hotel": _HOTEL_TEMPLATES[category][variant].format(locality=locality),
            "city": item["name"],
            "location": f"{locality}, {item['name']}",
            "room_type": room_types[variant],
            "price_per_night": price,
            "rooms_available": rng.randint(2, 18),
            "rating": round(rng.uniform(3.6, 4.9), 1),
            "amenities": rng.sample(_AMENITIES, k=4),
            "provider": "AURA simulated inventory",
            "category": category,
            "star_rating": star_rating,
            "simulated": True,
            "generated": True,
        })
    return hotels
