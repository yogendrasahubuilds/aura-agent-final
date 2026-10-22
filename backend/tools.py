"""AURA tool registry: search + booking + calculator.
Only registered tools can execute. LLM cannot call anything else.
Searches combine hand-curated mock data + dynamically generated options so
any Indian city / route returns comparable results."""
import json
from pathlib import Path
from typing import Optional
from data import MOVIES, HOTELS, FLIGHTS
from generator import (
    generate_movies, generate_hotels, generate_local_transport, generate_flights, generate_trains, generate_buses,
    get_cached_generated, annotate_with_comparison, resolve_city,
)

MOCK_DATA_DIR = Path(__file__).parent / "mock_data"


def _load_mock_options(intent: str) -> list[dict]:
    with (MOCK_DATA_DIR / f"{intent}.json").open(encoding="utf-8") as data_file:
        return json.load(data_file)


TRAIN_OPTIONS = _load_mock_options("train")
BUS_OPTIONS = _load_mock_options("bus")
CRICKET_OPTIONS = _load_mock_options("cricket")
CONCERT_OPTIONS = _load_mock_options("concert")
HOTEL_OPTIONS = _load_mock_options("hotel")
LOCAL_TRANSPORT_OPTIONS = _load_mock_options("local_transport")
_ROUTE_CACHE: dict[str, dict] = {}

TIME_WINDOWS = {
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 29),
}


def _hour_in_window(hhmm: str, window: Optional[str]) -> bool:
    if not window or window not in TIME_WINDOWS:
        return True
    try:
        h = int(hhmm.split(":")[0])
    except Exception:
        return True
    start, end = TIME_WINDOWS[window]
    if window == "night":
        return h >= 21 or h < 5
    return start <= h < end


def movie_search(city: Optional[str] = None, movie: Optional[str] = None, time_window: Optional[str] = None, **_):
    city_c = resolve_city(city) if city else None
    # Curated matches
    curated = list(MOVIES)
    if city_c:
        curated = [m for m in curated if m["city"].lower() == city_c.lower()]
    if movie:
        q = movie.lower().strip()
        curated = [m for m in curated if q in m["movie"].lower()]
    # Generated to always have 5-8 total
    generated = generate_movies(city_c or (city or "Delhi"), movie, count=6)
    if movie:
        q = movie.lower().strip()
        generated = [g for g in generated if q in g["movie"].lower() or g["movie"].lower() in q] or generated
    combined = curated + generated
    if time_window:
        combined = [m for m in combined if _hour_in_window(m["time"], time_window)]
    combined = combined[:8]
    return annotate_with_comparison(combined, "price")


def hotel_search(city: Optional[str] = None, **_):
    city_c = resolve_city(city) if city else None
    curated = list(HOTELS)
    curated.extend(HOTEL_OPTIONS)
    if city_c:
        curated = [h for h in curated if h["city"].lower() == city_c.lower()]
    generated = generate_hotels(city_c or (city or "Delhi"), count=max(0, 10 - len(curated)))
    combined = (curated + generated)[:10]
    return annotate_with_comparison(combined, "price_per_night")


def _max_eight_with_price_extremes(curated: list[dict], generated: list[dict]) -> list[dict]:
    if len(curated) + len(generated) <= 8:
        return curated + generated
    curated = curated[:8]
    remaining = 8 - len(curated)
    if remaining <= 0:
        return curated
    ordered = sorted(generated, key=lambda option: option.get("price", 0))
    if remaining == 1 or len(ordered) <= remaining:
        return curated + ordered[:remaining]
    selected = ordered[:remaining - 1] + [ordered[-1]]
    return curated + selected


def flight_search(source: Optional[str] = None, destination: Optional[str] = None, time_window: Optional[str] = None, date: Optional[str] = None, **_):
    src_c = resolve_city(source) if source else None
    dst_c = resolve_city(destination) if destination else None
    curated = list(FLIGHTS)
    if src_c:
        curated = [f for f in curated if f["source"].lower() == src_c.lower()]
    if dst_c:
        curated = [f for f in curated if f["destination"].lower() == dst_c.lower()]
    generated = []
    if src_c and dst_c and src_c.lower() != dst_c.lower():
        generated = generate_flights(src_c, dst_c, count=6, travel_date=date)
    combined = _max_eight_with_price_extremes(curated, generated)
    if time_window:
        combined = [f for f in combined if _hour_in_window(f["departure"], time_window)]
    combined = combined[:8]
    return annotate_with_comparison(combined, "price")


def _route_search(options: list[dict], source: Optional[str], destination: Optional[str], date: Optional[str], kind: str) -> list[dict]:
    source_c = resolve_city(source) if source else None
    destination_c = resolve_city(destination) if destination else None
    results = options
    if source_c:
        results = [option for option in results if option["source"].lower() == source_c.lower()]
    if destination_c:
        results = [option for option in results if option["destination"].lower() == destination_c.lower()]
    if source_c and destination_c and source_c.lower() != destination_c.lower():
        generated = (
            generate_trains(source_c, destination_c, count=6, travel_date=date)
            if kind == "train"
            else generate_buses(source_c, destination_c, count=6, travel_date=date)
        )
        results = _max_eight_with_price_extremes(results, generated)
    return annotate_with_comparison(results, "price")


def train_search(source: Optional[str] = None, destination: Optional[str] = None, date: Optional[str] = None, **_):
    return _route_search(TRAIN_OPTIONS, source, destination, date, "train")


def bus_search(source: Optional[str] = None, destination: Optional[str] = None, date: Optional[str] = None, **_):
    return _route_search(BUS_OPTIONS, source, destination, date, "bus")


def _event_search(options: list[dict], city: Optional[str], date: Optional[str]) -> list[dict]:
    city_c = resolve_city(city) if city else None
    results = options
    if city_c:
        results = [option for option in results if option["city"].lower() == city_c.lower()]
    if date:
        results = [option for option in results if option["date"] == date]
    return annotate_with_comparison(results, "price")


def cricket_search(city: Optional[str] = None, date: Optional[str] = None, **_):
    return _event_search(CRICKET_OPTIONS, city, date)


def concert_search(city: Optional[str] = None, date: Optional[str] = None, **_):
    return _event_search(CONCERT_OPTIONS, city, date)


def local_transport_search(city: Optional[str] = None, **_):
    city_c = resolve_city(city) if city else None
    options = [
        {**option, "city": city_c or option["city"]}
        for option in LOCAL_TRANSPORT_OPTIONS
        if not city_c or option["city"].lower() == city_c.lower()
    ]
    if city_c:
        options.extend(generate_local_transport(city_c))
    return annotate_with_comparison(options, "price_per_day")


def calculator(unit_price: float, quantity: int, nights: int = 1) -> dict:
    subtotal = float(unit_price) * int(quantity) * int(nights)
    tax = round(subtotal * 0.18, 2)  # 18% GST
    total = round(subtotal + tax, 2)
    return {"subtotal": round(subtotal, 2), "tax": tax, "total": total, "currency": "INR"}


TOOL_REGISTRY = {
    "movie_search": {"fn": movie_search, "risk": "low"},
    "hotel_search": {"fn": hotel_search, "risk": "low"},
    "flight_search": {"fn": flight_search, "risk": "low"},
    "calculator": {"fn": calculator, "risk": "low"},
    "movie_booking": {"fn": None, "risk": "medium"},
    "hotel_booking": {"fn": None, "risk": "medium"},
    "flight_booking": {"fn": None, "risk": "medium"},
}


def run_tool(name: str, **kwargs):
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {name}")
    entry = TOOL_REGISTRY[name]
    if entry["fn"] is None:
        raise ValueError(f"Tool {name} must be invoked via confirmed booking flow.")
    return entry["fn"](**kwargs)


def get_option_by_id(intent: str, option_id: str):
    # Try generated cache first
    cached = get_cached_generated(option_id)
    if cached:
        return cached
    if intent in ("train", "bus") and option_id in _ROUTE_CACHE:
        return _ROUTE_CACHE[option_id]
    if intent == "movie":
        return next((m for m in MOVIES if m["id"] == option_id), None)
    if intent == "hotel":
        return next((h for h in HOTELS + HOTEL_OPTIONS if h["id"] == option_id), None)
    if intent == "flight":
        return next((f for f in FLIGHTS if f["id"] == option_id), None)
    options = {
        "train": TRAIN_OPTIONS,
        "bus": BUS_OPTIONS,
        "cricket": CRICKET_OPTIONS,
        "concert": CONCERT_OPTIONS,
        "hotel": HOTEL_OPTIONS,
        "local_transport": LOCAL_TRANSPORT_OPTIONS,
    }.get(intent, [])
    option = next((item for item in options if item["id"] == option_id), None)
    if option:
        return option
    return None
