"""AURA tool registry: search + booking + calculator.
Only registered tools can execute. LLM cannot call anything else."""
from typing import Optional
from data import MOVIES, HOTELS, FLIGHTS

TIME_WINDOWS = {
    "morning": (5, 12),
    "afternoon": (12, 17),
    "evening": (17, 21),
    "night": (21, 29),  # 29 handles 24+5 wrap conceptually, we only compare hours
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
    results = MOVIES
    if city:
        results = [m for m in results if m["city"].lower() == city.lower()]
    if movie:
        q = movie.lower().strip()
        results = [m for m in results if q in m["movie"].lower() or m["movie"].lower() in q]
    if time_window:
        results = [m for m in results if _hour_in_window(m["time"], time_window)]
    return results[:8]


def hotel_search(city: Optional[str] = None, **_):
    results = HOTELS
    if city:
        results = [h for h in results if h["city"].lower() == city.lower()]
    return results[:8]


def flight_search(source: Optional[str] = None, destination: Optional[str] = None, time_window: Optional[str] = None, **_):
    results = FLIGHTS
    if source:
        results = [f for f in results if f["source"].lower() == source.lower()]
    if destination:
        results = [f for f in results if f["destination"].lower() == destination.lower()]
    if time_window:
        results = [f for f in results if _hour_in_window(f["departure"], time_window)]
    return results[:8]


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
    # Booking tools are "medium risk" — require explicit user confirmation at the API layer.
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
    if intent == "movie":
        return next((m for m in MOVIES if m["id"] == option_id), None)
    if intent == "hotel":
        return next((h for h in HOTELS if h["id"] == option_id), None)
    if intent == "flight":
        return next((f for f in FLIGHTS if f["id"] == option_id), None)
    return None
