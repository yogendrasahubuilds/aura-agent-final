"""AURA tool registry: search + booking + calculator.
Only registered tools can execute. LLM cannot call anything else.
Searches combine hand-curated mock data + dynamically generated options so
any Indian city / route returns comparable results."""
from typing import Optional
from data import MOVIES, HOTELS, FLIGHTS
from generator import (
    generate_movies, generate_hotels, generate_flights,
    get_cached_generated, annotate_with_comparison, resolve_city,
)

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
    if city_c:
        curated = [h for h in curated if h["city"].lower() == city_c.lower()]
    generated = generate_hotels(city_c or (city or "Delhi"), count=6)
    combined = (curated + generated)[:8]
    return annotate_with_comparison(combined, "price_per_night")


def flight_search(source: Optional[str] = None, destination: Optional[str] = None, time_window: Optional[str] = None, **_):
    src_c = resolve_city(source) if source else None
    dst_c = resolve_city(destination) if destination else None
    curated = list(FLIGHTS)
    if src_c:
        curated = [f for f in curated if f["source"].lower() == src_c.lower()]
    if dst_c:
        curated = [f for f in curated if f["destination"].lower() == dst_c.lower()]
    generated = []
    if src_c and dst_c and src_c.lower() != dst_c.lower():
        generated = generate_flights(src_c, dst_c, count=6)
    combined = curated + generated
    if time_window:
        combined = [f for f in combined if _hour_in_window(f["departure"], time_window)]
    combined = combined[:8]
    return annotate_with_comparison(combined, "price")


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
    if intent == "movie":
        return next((m for m in MOVIES if m["id"] == option_id), None)
    if intent == "hotel":
        return next((h for h in HOTELS if h["id"] == option_id), None)
    if intent == "flight":
        return next((f for f in FLIGHTS if f["id"] == option_id), None)
    return None
