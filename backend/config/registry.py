"""Allow-listed mock tools available to AURA's task planner."""
from typing import Any
from datetime import date, timedelta
import math
import re

from tools import (
    bus_search,
    concert_search,
    cricket_search,
    flight_search,
    hotel_search,
    local_transport_search,
    movie_search,
    train_search,
)


def _flight(parameters: dict, context: dict) -> dict:
    params = dict(parameters)
    params.setdefault("date", context.get("date"))
    return {
        "date": params.get("date"),
        "source": params.get("source"),
        "destination": params.get("destination"),
        "results": flight_search(**params),
        "simulated": True,
    }


def _hotel(parameters: dict, context: dict) -> dict:
    params = dict(parameters)
    params.setdefault("check_in", context.get("date"))
    return {
        "date": params.get("check_in"),
        "city": params.get("city") or context.get("destination"),
        "results": hotel_search(**params),
        "simulated": True,
    }


def _movie(parameters: dict, context: dict) -> dict:
    params = dict(parameters)
    params.setdefault("date", context.get("date"))
    return {
        "date": params.get("date"),
        "city": params.get("city"),
        "results": movie_search(**params),
        "simulated": True,
    }


def _train(parameters: dict, _context: dict) -> dict:
    return {
        "source": parameters.get("source"),
        "destination": parameters.get("destination"),
        "date": parameters.get("date"),
        "results": train_search(**parameters),
        "simulated": True,
    }


def _bus(parameters: dict, _context: dict) -> dict:
    return {
        "source": parameters.get("source"),
        "destination": parameters.get("destination"),
        "date": parameters.get("date"),
        "results": bus_search(**parameters),
        "simulated": True,
    }


def _cricket(parameters: dict, _context: dict) -> dict:
    return {
        "city": parameters.get("city"),
        "date": parameters.get("date"),
        "results": cricket_search(**parameters),
        "simulated": True,
    }


def _concert(parameters: dict, _context: dict) -> dict:
    return {
        "city": parameters.get("city"),
        "date": parameters.get("date"),
        "results": concert_search(**parameters),
        "simulated": True,
    }


def _local_transport(parameters: dict, _context: dict) -> dict:
    return {
        "city": parameters.get("city"),
        "days": parameters.get("days", 1),
        "results": local_transport_search(**parameters),
        "simulated": True,
    }


def _budget(parameters: dict, _context: dict) -> dict:
    budget = float(parameters["budget"])
    return {
        "budget": budget,
        "currency": "INR",
        "allocation": {
            "transport": round(budget * 0.45, 2),
            "stay": round(budget * 0.35, 2),
            "activities": round(budget * 0.20, 2),
        },
        "simulated": True,
    }


def _trip(parameters: dict, context: dict) -> dict:
    destination = parameters["destination"]
    start_date = parameters.get("start_date") or context.get("date")
    nights = parameters.get("nights", 1)
    interests = parameters.get("interests") or "local highlights"
    try:
        start = date.fromisoformat(start_date)
    except (TypeError, ValueError):
        start = None
    return {
        "source": parameters.get("source"),
        "destination": destination,
        "start_date": start_date,
        "nights": nights,
        "itinerary": [
            {
                "day": day,
                "activity": f"Explore {destination}: {interests} (mock itinerary)",
                "date": (start + timedelta(days=day - 1)).isoformat() if start else start_date,
            }
            for day in range(1, nights + 2)
        ],
        "simulated": True,
    }


def _tool(description: str, required: tuple[str, ...], parameters: tuple[str, ...], handler):
    return {
        "name": description[0],
        "description": description[1],
        "required_parameters": list(required),
        "parameters": list(parameters),
        "handler": handler,
    }


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "flight": _tool(
        ("flight", "Search simulated flights between two cities."),
        ("source", "destination", "date"),
        ("source", "destination", "date", "time_window", "passengers"),
        _flight,
    ),
    "train": _tool(
        ("train", "Find simulated train options for a route."),
        ("source", "destination", "date"),
        ("source", "destination", "date", "passengers"),
        _train,
    ),
    "bus": _tool(
        ("bus", "Find simulated bus options for a route."),
        ("source", "destination", "date"),
        ("source", "destination", "date", "passengers"),
        _bus,
    ),
    "hotel": _tool(
        ("hotel", "Search simulated hotel options in a city."),
        ("city", "check_in"),
        ("city", "check_in", "nights", "guests"),
        _hotel,
    ),
    "movie": _tool(
        ("movie", "Search simulated movie showings."),
        ("city", "date"),
        ("city", "date", "movie", "time_window", "tickets"),
        _movie,
    ),
    "cricket": _tool(
        ("cricket", "Find simulated cricket events in a city."),
        ("city", "date"),
        ("city", "date"),
        _cricket,
    ),
    "concert": _tool(
        ("concert", "Find simulated concerts in a city."),
        ("city", "date"),
        ("city", "date"),
        _concert,
    ),
    "local_transport": _tool(
        ("local_transport", "Estimate simulated local transport costs in a city."),
        ("city",),
        ("city", "days"),
        _local_transport,
    ),
    "budget_optimizer": _tool(
        ("budget_optimizer", "Create a simulated budget allocation."),
        ("budget",),
        ("budget", "city", "days"),
        _budget,
    ),
    "trip_planner": _tool(
        ("trip_planner", "Create a simulated trip itinerary."),
        ("source", "destination", "start_date"),
        ("source", "destination", "start_date", "nights", "travelers", "budget", "preference", "interests"),
        _trip,
    ),
}


def tool_descriptions() -> list[dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "description": item["description"],
            "required_parameters": item["required_parameters"],
            "parameters": item["parameters"],
        }
        for item in TOOL_REGISTRY.values()
    ]


def validate_plan(steps: Any) -> list[dict[str, Any]]:
    """Reject malformed, unknown, or incomplete tool calls before execution."""
    if not isinstance(steps, list) or not steps or len(steps) > 12:
        raise ValueError("The plan must contain between 1 and 12 steps.")

    validated = []
    available = set()
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or not isinstance(step.get("tool"), str):
            raise ValueError(f"Plan step {index + 1} is malformed.")
        name = step["tool"]
        entry = TOOL_REGISTRY.get(name)
        if entry is None:
            raise ValueError(f"Tool '{name}' is not in AURA's allow-list.")
        params = step.get("parameters")
        if not isinstance(params, dict):
            raise ValueError(f"Parameters for '{name}' must be an object.")
        unknown = set(params) - set(entry["parameters"])
        if unknown:
            raise ValueError(f"Unsupported parameter(s) for '{name}': {', '.join(sorted(unknown))}.")
        for key, value in params.items():
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValueError(f"Parameter '{key}' for '{name}' must be a scalar value.")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Parameter '{key}' for '{name}' must be finite.")
            if isinstance(value, str):
                params[key] = re.sub(
                    r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
                    "",
                    value,
                ).strip()[:250]

        missing = [
            key for key in entry["required_parameters"]
            if not params.get(key) and not (
                key == "check_in" and "date" in available
            ) and not (
                key == "date" and "date" in available
            )
        ]
        if missing:
            raise MissingToolParameters(name, missing[0])
        if name == "hotel" and not params.get("check_in") and "date" in available:
            params["check_in"] = "$previous.date"
        validated.append({"tool": name, "parameters": params, "status": "pending"})
        available.update(key for key, value in params.items() if value)
        if name in ("flight", "train", "bus", "movie", "concert", "cricket", "trip_planner"):
            available.add("date")
    return validated


class MissingToolParameters(ValueError):
    def __init__(self, tool: str, parameter: str):
        self.tool = tool
        self.parameter = parameter
        super().__init__(f"{tool}:{parameter}")


def resolve_parameters(parameters: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    resolved = {}
    for key, value in parameters.items():
        if value == "$previous.date":
            resolved[key] = previous.get("date")
        else:
            resolved[key] = value
    return resolved


def run_registered_tool(name: str, parameters: dict[str, Any], context: dict[str, Any]) -> dict:
    entry = TOOL_REGISTRY.get(name)
    if entry is None:
        raise ValueError(f"Tool '{name}' is not in AURA's allow-list.")
    result = entry["handler"](parameters, context)
    if not isinstance(result, dict):
        raise TypeError(f"Tool '{name}' returned an invalid result.")
    return result
