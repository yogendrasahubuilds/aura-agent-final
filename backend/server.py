"""AURA — Autonomous Universal Resource Agent (FastAPI backend).
All bookings are SIMULATED / DEMO."""
from fastapi import FastAPI, APIRouter, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import os
import logging
import re
import asyncio
import secrets
from copy import deepcopy
import bcrypt
import jwt
from jwt import InvalidTokenError
from pymongo.errors import DuplicateKeyError
from booking_pricing import price_booking

from agent import (
    build_plan,
    conversational_turn,
    create_task_plan,
    extract_trip_details,
    missing_parameter_question,
    sanitize_user_input,
    summarize_trip_results,
)
import agent as agent_parser
from config.registry import (
    MissingToolParameters,
    TOOL_REGISTRY,
    resolve_parameters,
    run_registered_tool,
    tool_descriptions,
    validate_plan,
)
from tools import get_option_by_id
from booking import create_mock_booking, verify_booking
from data import SUPPORTED_CITIES
from generator import CITIES as GEN_CITIES
from trip_planner import build_destination_trip, extract_destination_request

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").strip().lower() != "false"
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(
    mongo_url,
    serverSelectionTimeoutMS=2000 if not AUTH_ENABLED else 500,
    connectTimeoutMS=2000 if not AUTH_ENABLED else 500,
    socketTimeoutMS=2000 if not AUTH_ENABLED else 500,
)
db = client[os.environ["DB_NAME"]]


class MemoryCursor:
    def __init__(self, documents: list[dict]):
        self.documents = documents

    def sort(self, key: str, direction: int):
        self.documents.sort(key=lambda item: _memory_value(item, key), reverse=direction < 0)
        return self

    async def to_list(self, length: Optional[int] = None):
        return deepcopy(self.documents[:length] if length is not None else self.documents)


def _memory_value(document: dict, path: str):
    value = document
    for part in path.split("."):
        if isinstance(value, list):
            try:
                value = value[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _memory_set(document: dict, path: str, value: Any):
    parts = path.split(".")
    target = document
    for part in parts[:-1]:
        if isinstance(target, list):
            target = target[int(part)]
        else:
            target = target.setdefault(part, {})
    target[parts[-1]] = deepcopy(value)


class MemoryCollection:
    def __init__(self):
        self.documents: list[dict] = []

    async def insert_one(self, document: dict):
        self.documents.append(deepcopy(document))

    async def find_one(self, query: dict, projection: Optional[dict] = None):
        document = next(
            (
                item for item in self.documents
                if all(_memory_value(item, key) == value for key, value in query.items())
            ),
            None,
        )
        if document is None:
            return None
        result = deepcopy(document)
        for key, include in (projection or {}).items():
            if include == 0:
                result.pop(key, None)
        return result

    def find(self, query: dict, projection: Optional[dict] = None):
        matched = [
            document for document in self.documents
            if all(_memory_value(document, key) == value for key, value in query.items())
        ]
        projected = []
        for document in matched:
            result = deepcopy(document)
            for key, include in (projection or {}).items():
                if include == 0:
                    result.pop(key, None)
            projected.append(result)
        return MemoryCursor(projected)

    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        document = next(
            (
                item for item in self.documents
                if all(_memory_value(item, key) == value for key, value in query.items())
            ),
            None,
        )
        if document is None and upsert:
            document = deepcopy(query)
            self.documents.append(document)
        if document:
            for key, value in update.get("$set", {}).items():
                _memory_set(document, key, value)
        return type("UpdateResult", (), {"matched_count": int(document is not None)})()

    async def create_index(self, *_args, **_kwargs):
        return None


class InMemoryDatabase:
    def __init__(self):
        self.collections: dict[str, MemoryCollection] = {}

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self.collections:
            self.collections[name] = MemoryCollection()
        return self.collections[name]


DEFAULT_USER = {"id": "default-user", "name": "Guest", "email": "guest@local"}
using_memory_fallback = False


app = FastAPI(title="AURA API",
              description="Autonomous Universal Resource Agent — Simulated Bookings")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ------------- Models -------------
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: str = Field(default="anonymous", min_length=1, max_length=100)
    tool: Optional[str] = None
    mode: str = "agent"
    conversation: List[dict] = Field(default_factory=list)
    reset: bool = False


class RunRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)


class ExecuteStepRequest(RunRequest):
    index: int = Field(ge=0, le=11)


class SearchRequest(BaseModel):
    intent: str
    params: dict


class ConfirmRequest(BaseModel):
    intent: str
    option_id: str
    quantity: int = Field(default=1, ge=1)
    nights: int = Field(default=1, ge=1)
    rooms: int = Field(default=1, ge=1)
    promo_code: Optional[str] = None
    insurance: bool = False


class ConfirmPlanRequest(BaseModel):
    items: List[ConfirmRequest] = Field(min_length=1, max_length=10)


class BookingPassenger(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=120)
    gender: str = Field(min_length=1, max_length=20)

    @field_validator("name")
    @classmethod
    def clean_passenger_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Passenger name is required.")
        return cleaned

    @field_validator("gender")
    @classmethod
    def clean_passenger_gender(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Passenger gender is required.")
        return cleaned


class BookingContact(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=10, max_length=15)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        cleaned = re.sub(r"[+\s()-]", "", value)
        if not cleaned.isdigit() or not 10 <= len(cleaned) <= 15:
            raise ValueError("Enter a valid contact phone number.")
        return cleaned


class BookRequest(BaseModel):
    intent: str
    option_id: str
    user_id: str = "anonymous"
    run_id: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    nights: int = Field(default=1, ge=1)
    rooms: int = Field(default=1, ge=1)
    confirmed: bool = False
    user_request: Optional[str] = None
    seats: Optional[List[str]] = None
    passengers: List[BookingPassenger]
    contact: BookingContact
    promo_code: Optional[str] = None
    insurance: bool = False
    payment_method: str = Field(pattern="^(UPI|Card|Net Banking)$")


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Name is required.")
        return name


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password_size(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Invalid email or password.")
        return value


# ------------- Helpers -------------
def _jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="JWT_SECRET is not configured.")
    return secret


def _public_user(user: dict) -> dict:
    return {"id": user["_id"], "name": user["name"], "email": user["email"]}


def _auth_response(user: dict) -> dict:
    token = jwt.encode(
        {
            "sub": user["_id"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        },
        _jwt_secret(),
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not AUTH_ENABLED:
        return DEFAULT_USER.copy()
    unauthorized = HTTPException(
        status_code=401,
        detail="Valid bearer token required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized
    try:
        claims = jwt.decode(
            authorization[7:].strip(), _jwt_secret(), algorithms=["HS256"]
        )
        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise unauthorized
    except InvalidTokenError:
        raise unauthorized from None

    user = await db.users.find_one({"_id": user_id}, {"password_hash": 0})
    if not user:
        raise unauthorized
    return _public_user(user)


def _apply_authenticated_owner(request_model: Any, current_user: Any) -> None:
    # Endpoint functions are also called directly by unit tests; HTTP requests
    # always receive the validated user from FastAPI's dependency injection.
    if isinstance(current_user, dict):
        request_model.user_id = current_user["id"]


async def _log_step(
    booking_id: Optional[str],
    step: str,
    status: str = "done",
    user_id: str = "anonymous",
):
    doc = {
        "booking_id": booking_id,
        "user_id": user_id,
        "step": step,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.execution_logs.insert_one(doc)
    except Exception as e:
        logger.warning(f"log_step failed: {e}")


def _conversation_question(
    details: dict,
    sections: list[str],
    standalone: bool = False,
) -> Optional[str]:
    if standalone:
        if not details.get("city"):
            return "Which city should I search?"
        if "hotel" in sections and not details.get("start_date"):
            return "What is your hotel check-in date?"
        if "local_transport" in sections and not details.get("days"):
            return "For how many days do you need local transport?"
        return None
    if any(tool in sections for tool in ("flight", "train", "bus")):
        if not details.get("source"):
            return "Which city are you starting from?"
        if not details.get("destination"):
            return "Where would you like to go?"
        if not details.get("start_date"):
            return "What date would you like to start?"
    return None


def _requested_conversation_sections(text: str) -> tuple[list[str], bool]:
    lowered = text.lower()
    transport = [
        tool for tool in ("flight", "train", "bus")
        if re.search(rf"\b{tool}s?\b", lowered)
    ]
    hotel = bool(re.search(r"\b(hotel|hotels|stay|room|accommodation)\b", lowered))
    local = bool(re.search(
        r"\b(local transport|transport estimates|getting around|local travel|"
        r"auto(?:s)?|taxi|metro|local bus)\b",
        lowered,
    ))
    explicit_request = bool(transport or hotel or local)
    standalone = explicit_request and not transport and (hotel or local)
    if standalone:
        return [tool for tool, requested in (("hotel", hotel), ("local_transport", local)) if requested], True
    if transport:
        sections = transport
        if hotel:
            sections.append("hotel")
    elif explicit_request:
        sections = ["hotel"] if hotel else ["local_transport"]
    else:
        sections = ["flight", "train", "hotel"]
    if local and "local_transport" not in sections:
        sections.append("local_transport")
    return sections, False


def _extract_requested_days(text: str) -> Optional[int]:
    match = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight)\s+days?\b", text, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).lower()
    return int(value) if value.isdigit() else {
        "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8,
    }[value]


def _trip_steps(details: dict, sections: list[str]) -> list[dict]:
    steps = []
    if details.get("budget") is not None:
        steps.append({"tool": "budget_optimizer", "parameters": {
            "budget": details["budget"],
            "city": details["destination"],
            "days": details["nights"] + 1,
        }})
    for tool in ("flight", "train", "bus"):
        if tool in sections:
            steps.append({"tool": tool, "parameters": {
                "source": details["source"],
                "destination": details["destination"],
                "date": details["start_date"],
                "passengers": details["travelers"],
            }})
    if "hotel" in sections:
        steps.append({"tool": "hotel", "parameters": {
            "city": details["destination"],
            "check_in": details["start_date"],
            "nights": details["nights"],
            "guests": details["travelers"],
        }})
    if "hotel" in sections or any(tool in sections for tool in ("flight", "train", "bus", "local_transport")):
        steps.append({"tool": "local_transport", "parameters": {
            "city": details["destination"],
            "days": details.get("days") or details["nights"] + 1,
        }})
    steps.append({"tool": "trip_planner", "parameters": {
        **details,
        "preference": details.get("preference") or "all",
        "interests": details.get("interests") or "local highlights",
    }})
    return steps


def _tier_options(options: list[dict], price_key: str, rating_key: Optional[str] = None) -> list[dict]:
    if len(options) < 3:
        return []
    ordered = sorted(options, key=lambda option: (option.get(price_key, 0), option.get(rating_key or "rating", 0)))
    if price_key == "price_per_night":
        budget = min(options, key=lambda option: float(option.get(price_key, 0)))
        comfort_options = [option for option in options if option.get("category") == "3-star"]
        comfort = max(
            comfort_options or ordered,
            key=lambda option: float(option.get("rating") or 0) / max(float(option.get(price_key) or 0), 1),
        )
        premium_options = [option for option in options if option.get("category") == "5-star"]
        premium = max(premium_options or ordered, key=lambda option: float(option.get(price_key, 0)))
        picks = (budget, comfort, premium)
    else:
        picks = (ordered[0], ordered[len(ordered) // 2], max(
            ordered, key=lambda option: (option.get(price_key, 0), option.get(rating_key or "rating", 0))
        ))
    tiers = []
    seen = set()
    for tier, option in zip(("Budget", "Comfort", "Premium"), picks):
        if option["id"] in seen:
            continue
        tiers.append({**option, "tier": tier})
        seen.add(option["id"])
    return tiers


def _duration_minutes(option: dict) -> Optional[int]:
    duration = str(option.get("duration") or "")
    match = re.search(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?", duration, re.IGNORECASE)
    if not match or not any(match.groups()):
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def _money(value: float) -> str:
    amount = round(float(value), 2)
    if amount.is_integer():
        return f"{int(amount):,}"
    return f"{amount:,.2f}".rstrip("0").rstrip(".")


def _explain_options(
    options: list[dict],
    intent: str,
    preference: Optional[str] = None,
    budget: Optional[float] = None,
    quantity: int = 1,
    nights: int = 1,
) -> tuple[list[dict], Optional[str]]:
    if not options:
        return [], None
    price_key = "price_per_night" if intent == "hotel" else (
        "price_per_day" if intent == "local_transport" else "price"
    )
    stay_duration = f"{nights} {'night' if nights == 1 else 'nights'}"

    def cost(option: dict) -> float:
        if intent == "hotel":
            return float(option.get(price_key) or 0) * nights
        if intent == "local_transport":
            return float(option.get(price_key) or 0)
        return float(option.get(price_key) or 0) * quantity

    cheapest = min(options, key=cost)
    affordable = [option for option in options if budget is None or cost(option) <= budget]
    candidates = affordable or options
    preference = (preference or "all").lower()
    if preference in ("budget", "cheapest"):
        recommended = min(candidates, key=cost)
    elif preference in ("premium", "luxury"):
        recommended = max(
            candidates,
            key=lambda option: (
                float(option.get("rating") or 0),
                cost(option),
            ),
        )
    elif intent in ("cricket", "concert") and any(option.get("tier") == "Comfort" for option in candidates):
        recommended = next(option for option in candidates if option.get("tier") == "Comfort")
    elif intent == "hotel" and any(option.get("rating") is not None for option in candidates):
        hotel_candidates = options if preference == "all" else candidates
        non_hostels = [
            option for option in hotel_candidates
            if option.get("category") != "Hostel/Budget"
            and "dorm" not in str(option.get("room_type", "")).lower()
        ] or hotel_candidates
        comfort_options = [option for option in non_hostels if option.get("category") == "3-star"]
        recommended = max(
            comfort_options or non_hostels,
            key=lambda option: float(option.get("rating") or 0)
            / max(float(option.get(price_key) or 0), 1),
        )
    elif any(_duration_minutes(option) is not None for option in candidates):
        cheapest_option = min(candidates, key=cost)
        base_cost = cost(cheapest_option)
        base_duration = _duration_minutes(cheapest_option)
        value_options = []
        for option in candidates:
            duration = _duration_minutes(option)
            saved = base_duration - duration if duration is not None and base_duration is not None else 0
            extra = cost(option) - base_cost
            value_options.append((extra / saved if saved > 0 else float("inf"), cost(option), option))
        recommended = min(value_options, key=lambda item: (item[0], item[1]))[2]
    else:
        recommended = min(candidates, key=cost)

    ordered_prices = sorted({cost(option) for option in options})
    next_price = next((price for price in ordered_prices if price > cost(cheapest)), None)
    fastest = min(
        (option for option in options if _duration_minutes(option) is not None),
        key=lambda option: _duration_minutes(option),
        default=None,
    )
    slowest = max(
        (option for option in options if _duration_minutes(option) is not None),
        key=lambda option: _duration_minutes(option),
        default=None,
    )
    tradeoff = None
    if intent in ("flight", "train", "bus") or intent == "transport":
        if fastest and cheapest and fastest.get("id") != cheapest.get("id"):
            minutes_saved = (_duration_minutes(cheapest) or 0) - (_duration_minutes(fastest) or 0)
            price_more = cost(fastest) - cost(cheapest)
            if minutes_saved > 0:
                faster_name = fastest.get("intent", intent)
                cheaper_name = cheapest.get("intent", intent)
                price_summary = (
                    f"costs Rs {_money(price_more)} more than"
                    if price_more >= 0
                    else f"is Rs {_money(abs(price_more))} cheaper than"
                )
                tradeoff = (
                    f"Fastest {faster_name} {price_summary} cheapest {cheaper_name} "
                    f"and saves {minutes_saved // 60}h {minutes_saved % 60}m."
                )
        if not tradeoff:
            if fastest and fastest.get("id") == cheapest.get("id"):
                tradeoff = "The fastest and cheapest options are the same."
            elif fastest:
                tradeoff = "The fastest and cheapest options have the same duration."
    elif intent == "hotel":
        recommended_rate = float(recommended.get(price_key) or 0)
        hotel_category = recommended.get("category") or "Comfort"
        tradeoff = (
            f"Recommended {hotel_category}: rated {recommended.get('rating', '—')} stars at "
            f"Rs {_money(recommended_rate)} per night "
            f"(Rs {_money(recommended_rate * nights)} for {stay_duration})."
        )
    elif intent == "local_transport":
        if next_price is not None:
            tradeoff = f"Cheapest estimate is Rs {_money(next_price - cost(cheapest))} less per day than the next option."
        else:
            tradeoff = "Daily estimates vary by local transport mode."
    elif intent in ("cricket", "concert"):
        premium = max(options, key=cost)
        if premium.get("id") != cheapest.get("id"):
            tradeoff = f"Premium tickets cost Rs {_money(cost(premium) - cost(cheapest))} more than Budget tickets."
        else:
            tradeoff = "Premium and Budget tickets have the same price."

    annotated = []
    for option in options:
        difference_from_cheapest = cost(option) - cost(cheapest)
        if intent == "hotel":
            rate = float(option.get(price_key) or 0)
            recommended_rate = float(recommended.get(price_key) or 0)
            rate_difference = rate - recommended_rate
            reason = (
                f"Rs {_money(abs(rate_difference))} "
                f"{'more' if rate_difference >= 0 else 'less'} per night than Recommended "
                f"(Rs {_money(abs(rate_difference) * nights)} "
                f"{'more' if rate_difference >= 0 else 'less'} for {stay_duration})."
            )
        elif intent == "local_transport":
            rate_difference = float(option.get(price_key) or 0) - float(cheapest.get(price_key) or 0)
            reason = (
                f"Rs {_money(abs(rate_difference))} "
                f"{'more' if rate_difference >= 0 else 'less'} per day than the cheapest estimate."
            )
        else:
            reason = f"Rs {_money(difference_from_cheapest)} more than the cheapest option."
        if budget is not None and cost(option) > budget:
            if intent == "hotel":
                over_per_night = (cost(option) - budget) / max(nights, 1)
                reason = (
                    f"Rs {_money(over_per_night)} over budget per night "
                    f"(Rs {_money(cost(option) - budget)} for {stay_duration})."
                )
            elif intent == "local_transport":
                reason = (
                    f"Rs {_money(cost(option) - budget)} over your local transport budget per day."
                )
            else:
                reason = f"Rs {_money(cost(option) - budget)} over your budget."
        elif intent == "hotel" and option.get("id") == recommended.get("id"):
            reason = tradeoff
        elif option.get("id") == recommended.get("id"):
            remaining = budget - cost(option) if budget is not None else None
            if remaining is not None:
                if intent == "hotel":
                    rate = float(option.get(price_key) or 0)
                    reason = (
                        f"Fits your budget at Rs {_money(rate)} per night "
                        f"(Rs {_money(rate * nights)} for {stay_duration}), "
                        f"with Rs {_money(remaining)} left."
                    )
                elif intent == "local_transport":
                    reason = (
                        f"Fits your budget at Rs {_money(option.get(price_key) or 0)} per day."
                    )
                else:
                    reason = f"Fits your budget with Rs {_money(remaining)} left."
            elif option.get("id") == cheapest.get("id") and next_price is not None:
                if intent == "local_transport":
                    reason = (
                        f"Cheapest estimate, Rs {_money(next_price - cost(option))} "
                        "less per day than the next option."
                    )
                else:
                    reason = f"Cheapest option, Rs {_money(next_price - cost(option))} less than the next one."
            elif option.get("id") == cheapest.get("id"):
                reason = "Cheapest estimate available per day." if intent == "local_transport" else "Cheapest option available."
            elif intent in ("cricket", "concert") and option.get("tier") == "Comfort":
                reason = f"Comfort tier costs Rs {_money(difference_from_cheapest)} more than Budget."
            elif fastest and option.get("id") == fastest.get("id") and slowest and slowest.get("id") != fastest.get("id"):
                saved = (_duration_minutes(slowest) or 0) - (_duration_minutes(fastest) or 0)
                if saved > 0:
                    reason = f"Fastest, saves {saved // 60}h {saved % 60}m compared to the slowest option."
            elif fastest and option.get("id") != cheapest.get("id") and _duration_minutes(option) is not None:
                saved = (_duration_minutes(cheapest) or 0) - (_duration_minutes(option) or 0)
                reason = (
                    f"Best value: Rs {_money(difference_from_cheapest)} more than cheapest, "
                    f"{max(saved, 0) // 60}h {max(saved, 0) % 60}m faster."
                )
            else:
                reason = "Best value based on the available price and quality."
        annotated.append({
            **option,
            "recommended": option.get("id") == recommended.get("id"),
            "reason": reason,
        })
    return annotated, tradeoff


def _annotate_tool_result(
    intent: str,
    result: dict,
    parameters: Optional[dict] = None,
    preference: Optional[str] = None,
    budget: Optional[float] = None,
) -> dict:
    if not result.get("results"):
        return result
    parameters = parameters or {}
    options, tradeoff = _explain_options(
        result["results"],
        intent,
        preference=preference or parameters.get("preference"),
        budget=budget if budget is not None else parameters.get("budget"),
        quantity=int(
            parameters.get("passengers")
            or parameters.get("guests")
            or parameters.get("days")
            or 1
        ),
        nights=int(parameters.get("nights") or 1),
    )
    options = [{**option, "tradeoff": tradeoff} for option in options]
    return {**result, "results": options, "tradeoff": tradeoff}


def _build_trip_preview(details: dict, sections: list[str], results: dict) -> dict:
    options = {}
    tradeoffs = {}
    for key in sections:
        tiers = results[key]["results"] if key == "local_transport" else _tier_options(
            results[key]["results"],
            "price_per_night" if key == "hotel" else "price",
            "rating" if key == "hotel" else None,
        )
        options[key], tradeoffs[key] = _explain_options(
            tiers,
            key,
            preference=details.get("preference"),
            budget=details.get("budget"),
            quantity=details.get("travelers", 1),
            nights=details.get("nights", 1),
        )
    return {
        "details": details,
        "sections": sections,
        "options": options,
        "tradeoffs": tradeoffs,
        "local_transport": results.get("local_transport", {}).get("results", []),
        "itinerary": results["trip_planner"].get("itinerary", []),
        "budget": details.get("budget"),
    }


def _stored_explanations(trip_plan: dict) -> dict:
    explanations = {}
    for section, options in trip_plan.get("options", {}).items():
        tradeoff = trip_plan.get("tradeoffs", {}).get(section)
        if isinstance(tradeoff, dict):
            tradeoff = tradeoff.get(
                trip_plan.get("defaults", {}).get("outbound", {}).get("intent")
            )
        explanations[section] = {
            "tradeoff": tradeoff,
            "options": [
                {
                    "id": option.get("id"),
                    "name": (
                        option.get("hotel") or option.get("airline") or option.get("train_name")
                        or option.get("operator") or option.get("match") or option.get("event")
                        or option.get("class") or option.get("intent")
                    ),
                    "intent": option.get("intent", section),
                    "reason": option.get("reason"),
                    "recommended": option.get("recommended", False),
                }
                for option in options
            ],
        }
    return explanations


def _why_reply(message: str, explanations: dict) -> Optional[str]:
    if not re.search(r"\bwhy\b", message, re.IGNORECASE):
        return None
    if not explanations:
        return "I don't have current results to explain yet. Share a route or event plan first."
    requested = None
    for keyword, intent in (
        ("flight", "flight"), ("train", "train"), ("bus", "bus"),
        ("hotel", "hotel"), ("ticket", "event"),
        ("cricket", "event"), ("concert", "event"),
    ):
        if re.search(rf"\b{keyword}s?\b", message, re.IGNORECASE):
            requested = intent
            break
    entries = []
    for section, data in explanations.items():
        options = data.get("options", [])
        selected = [option for option in options if requested is None or option.get("intent") == requested]
        if selected:
            entries.append((section, data, selected))
    if not entries:
        entries = [
            (section, data, data.get("options", []))
            for section, data in explanations.items()
            if data.get("options")
        ]
    if not entries:
        return "I don't have current results to explain yet. Share a route or event plan first."
    section, data, options = entries[0]
    option = next((item for item in options if item.get("recommended")), options[0])
    subject = option.get("name") or section.title()
    lines = [f"{subject} — {option.get('reason') or 'selected from the available mock results.'}"]
    if data.get("tradeoff"):
        lines.append(data["tradeoff"])
    return "\n".join(lines[:2])


def _event_cities(text: str) -> list[tuple[int, str]]:
    matches = []
    for alias in sorted(agent_parser.CITY_ALIASES, key=len, reverse=True):
        for match in re.finditer(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
            if not any(
                start <= match.start() < end
                for start, end, _city in matches
            ):
                matches.append((match.start(), match.end(), agent_parser.CITY_ALIASES[alias]))
    return [(start, city) for start, _end, city in sorted(matches)]


def _event_source_city(text: str, question_asked: bool = False) -> Optional[str]:
    for alias in sorted(agent_parser.CITY_ALIASES, key=len, reverse=True):
        if re.search(
            rf"\b(?:from|based\s+in|currently\s+in|located\s+in|i(?:'m|\s+am)\s+in)\s+{re.escape(alias)}\b",
            text,
            re.IGNORECASE,
        ):
            return agent_parser.CITY_ALIASES[alias]
    if question_asked:
        matches = _event_cities(text)
        if matches:
            return matches[-1][1]
    return None


def _group_size_missing(text: str, travelers: Optional[int]) -> bool:
    return travelers is None and bool(re.search(
        r"\b(?:my\s+friends?\s+and\s+i|friends?\s+and\s+i|with\s+my\s+friends?|"
        r"my\s+family\s+and\s+i|our\s+family)\b",
        text,
        re.IGNORECASE,
    ))


def _standalone_traveler_count(text: str) -> Optional[int]:
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }
    match = re.fullmatch(
        r"\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s*[.!]?\s*",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = match.group(1).lower()
    return int(value) if value.isdigit() else words[value]


def _event_tool_from_text(text: str) -> Optional[str]:
    if re.search(r"\b(concert|gig|live\s+show|music\s+show)\b", text, re.IGNORECASE):
        return "concert"
    if re.search(r"\b(cricket|match|vs\.?|versus|ipl|odi|t20)\b", text, re.IGNORECASE):
        return "cricket"
    return None


def _event_match_score(option: dict, text: str) -> int:
    labels = " ".join(str(option.get(key, "")) for key in ("match", "event")).lower()
    ignored = {
        "watch", "want", "see", "attend", "cricket", "concert", "match",
        "event", "live", "please", "tickets", "ticket", "in", "the",
    }
    words = set(re.findall(r"[a-z0-9]+", text.lower())) - ignored
    words -= {alias.lower() for alias in agent_parser.CITY_ALIASES}
    return sum(word in labels for word in words)


def _tier_event_options(options: list[dict]) -> list[dict]:
    ordered = sorted(options, key=lambda option: option.get("price", 0))
    if len(ordered) < 3:
        return []
    chosen = (ordered[0], ordered[len(ordered) // 2], ordered[-1])
    return [
        {**option, "tier": tier}
        for tier, option in zip(("Budget", "Comfort", "Premium"), chosen)
    ]


async def _conversational_event_plan(
    req: ChatRequest,
    message: str,
    conversation: list[dict],
    previous: Optional[dict],
    combined_user_text: str,
    parsed: dict,
    event_tool: str,
) -> dict:
    previous_details = (previous or {}).get("event_details", {})
    source = (
        _event_source_city(combined_user_text, bool((previous or {}).get("event_source_question_asked")))
        or previous_details.get("source")
        or parsed.get("source")
    )
    event_city = previous_details.get("event_city")
    mentions = _event_cities(combined_user_text)
    explicit_sources = {
        city for _position, city in mentions
        if _event_source_city(
            combined_user_text[max(0, _position - 30):_position + len(city)],
            False,
        ) == city
    }
    for match in re.finditer(r"\b(?:in|at)\s+([A-Za-z][A-Za-z .'-]+)", combined_user_text, re.IGNORECASE):
        candidate = agent_parser._extract_city(match.group(1).split(",")[0].strip())
        if candidate and candidate != source and candidate not in explicit_sources:
            event_city = candidate
            break
    if not event_city:
        event_city = parsed.get("destination") or previous_details.get("event_city")

    user_date = parsed.get("start_date")
    if user_date:
        try:
            user_date = datetime.fromisoformat(str(user_date)).date().isoformat()
        except ValueError:
            user_date = None
    travelers = parsed.get("travelers") or previous_details.get("travelers")
    if travelers is None and any(
        item.get("role") == "assistant" and "how many travelers" in item.get("content", "").lower()
        for item in conversation[-2:]
    ):
        travelers = _standalone_traveler_count(message)
    group_size_missing = _group_size_missing(combined_user_text, travelers)
    budget = parsed.get("budget")
    if budget is None:
        budget = previous_details.get("budget")
    preference = parsed.get("preference") or previous_details.get("preference") or "all"

    event_parameters = {"city": event_city} if event_city else {}
    event_results = run_registered_tool(event_tool, event_parameters, {}).get("results", [])
    if user_date:
        event_results = [option for option in event_results if option.get("date") == user_date]
    if not event_results:
        reply = "I couldn't find a matching mock event for that city or date. Try another event or city."
        conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {
                "messages": conversation,
                "event_active": True,
                "event_details": {
                    "source": source,
                    "event_city": event_city,
                    "event_tool": event_tool,
                    "travelers": travelers,
                    "budget": budget,
                },
            }},
            upsert=True,
        )
        return {"mode": "conversation", "reply": reply, "conversation": conversation, "trip_plan": None}

    best_score = max(_event_match_score(option, combined_user_text) for option in event_results)
    matching_events = [
        option for option in event_results
        if _event_match_score(option, combined_user_text) == best_score
    ]
    selected_event = matching_events[0]
    event_key = ("match" if event_tool == "cricket" else "event", "date", "city")
    matching_events = [
        option for option in event_results
        if all(option.get(key) == selected_event.get(key) for key in event_key)
    ]
    if not event_city:
        event_city = selected_event["city"]

    if not source:
        asked = bool((previous or {}).get("event_source_question_asked"))
        if asked:
            source = "Delhi"
        else:
            reply = "Which city are you traveling from?"
            conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
            await db.conversations.update_one(
                {"user_id": req.user_id},
                {"$set": {
                    "messages": conversation,
                    "event_active": True,
                    "event_source_question_asked": True,
                    "event_details": {
                        "event": selected_event,
                        "event_tool": event_tool,
                        "event_city": event_city,
                        "event_date": selected_event["date"],
                        "travelers": travelers,
                        "budget": budget,
                    },
                }},
                upsert=True,
            )
            return {
                "mode": "conversation",
                "reply": reply,
                "conversation": conversation,
                "trip_plan": None,
            }

    if group_size_missing and not (previous or {}).get("event_traveler_question_asked"):
        reply = "How many travelers should I include?"
        conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {
                "messages": conversation,
                "event_active": True,
                "event_source_question_asked": bool((previous or {}).get("event_source_question_asked")),
                "event_traveler_question_asked": True,
                "event_details": {
                    "source": source,
                    "event_city": event_city,
                    "event_tool": event_tool,
                    "event_date": selected_event["date"],
                    "budget": budget,
                },
            }},
            upsert=True,
        )
        return {
            "mode": "conversation",
            "reply": reply,
            "conversation": conversation,
            "trip_plan": None,
        }
    travelers = travelers or previous_details.get("travelers") or 1

    event_options = _tier_event_options(matching_events)
    if len(event_options) != 3:
        reply = "I found the event, but its mock data has fewer than three ticket tiers, so I can't build the combined plan yet."
        conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {"messages": conversation, "event_active": True}},
            upsert=True,
        )
        return {"mode": "conversation", "reply": reply, "conversation": conversation, "trip_plan": None}

    event_date = datetime.fromisoformat(selected_event["date"]).date()
    outbound_date = (event_date - timedelta(days=1)).isoformat()
    return_date = (event_date + timedelta(days=1)).isoformat()
    steps = []
    for tool in ("flight", "train", "bus"):
        steps.append({
            "tool": tool,
            "parameters": {
                "source": source,
                "destination": event_city,
                "date": outbound_date,
                "passengers": travelers,
            },
        })
    steps.extend([
        {
            "tool": "hotel",
            "parameters": {
                "city": event_city,
                "check_in": selected_event["date"],
                "nights": 1,
                "guests": travelers,
            },
        },
        {
            "tool": event_tool,
            "parameters": {"city": event_city, "date": selected_event["date"]},
        },
        {"tool": "local_transport", "parameters": {"city": event_city, "days": 2}},
    ])
    for tool in ("flight", "train", "bus"):
        steps.append({
            "tool": tool,
            "parameters": {
                "source": event_city,
                "destination": source,
                "date": return_date,
                "passengers": travelers,
            },
        })
    steps = validate_plan(steps)
    tool_results = {
        (step["tool"], index): run_registered_tool(step["tool"], step["parameters"], {})
        for index, step in enumerate(steps)
    }
    outbound_options = []
    return_options = []
    for index, tool in enumerate(("flight", "train", "bus")):
        result = tool_results[(tool, index)]["results"]
        outbound_options.extend(
            [{**option, "intent": tool, "travel_date": outbound_date} for option in result]
        )
    for index, tool in enumerate(("flight", "train", "bus"), start=6):
        result = tool_results[(tool, index)]["results"]
        return_options.extend(
            [{**option, "intent": tool, "travel_date": return_date} for option in result]
        )
    hotels, hotel_tradeoff = _explain_options(
        _tier_options(
            tool_results[("hotel", 3)]["results"],
            "price_per_night",
            "rating",
        ),
        "hotel",
        preference=preference,
        budget=budget,
        quantity=travelers,
    )
    event_options, event_tradeoff = _explain_options(
        _tier_event_options(tool_results[(event_tool, 4)]["results"]),
        event_tool,
        preference=preference,
        budget=budget,
        quantity=travelers,
    )
    outbound_options, outbound_tradeoff = _explain_options(
        outbound_options,
        "transport",
        preference=preference,
        budget=budget,
        quantity=travelers,
    )
    return_groups = []
    return_tradeoffs = {}
    for mode in ("flight", "train", "bus"):
        mode_options, mode_tradeoff = _explain_options(
            [option for option in return_options if option["intent"] == mode],
            "transport",
            preference=preference,
            budget=budget,
            quantity=travelers,
        )
        return_groups.extend(mode_options)
        return_tradeoffs[mode] = mode_tradeoff
    return_options = return_groups
    local_options = tool_results[("local_transport", 5)]["results"]
    default_outbound = next(option for option in outbound_options if option["recommended"])
    default_return = next(
        option for option in return_options
        if option["intent"] == default_outbound["intent"] and option["recommended"]
    )
    defaults = {
        "event": {"intent": event_tool, "option": next(option for option in event_options if option["recommended"])},
        "outbound": {"intent": default_outbound["intent"], "option": default_outbound},
        "hotel": {"intent": "hotel", "option": next(option for option in hotels if option["recommended"])},
        "return": {"intent": default_return["intent"], "option": default_return},
        "local": {
            "intent": "local_transport",
            "option": min(local_options, key=lambda option: option["price_per_day"]),
        },
    }
    trip_plan = {
        "kind": "event_travel",
        "details": {
            "source": source,
            "event_city": event_city,
            "event_type": event_tool,
            "event": selected_event.get("match") or selected_event.get("event"),
            "event_date": selected_event["date"],
            "travelers": travelers,
            "budget": budget,
            "preference": preference,
        },
        "options": {
            "event": event_options,
            "outbound": outbound_options,
            "hotel": hotels,
            "return": return_options,
            "local": local_options,
        },
        "tradeoffs": {
            "event": event_tradeoff,
            "outbound": outbound_tradeoff,
            "hotel": hotel_tradeoff,
            "return": return_tradeoffs,
        },
        "defaults": defaults,
        "local_transport": min(local_options, key=lambda option: option["price_per_day"]),
        "local_days": 2,
        "steps": steps,
    }
    reply = "I found a combined event and travel plan using mock options. Review the timeline and cost breakdown in the panel."
    run_id = str(uuid4())
    run_doc = {
        "run_id": run_id,
        "user_id": req.user_id,
        "request": combined_user_text,
        "intents": [step["tool"] for step in steps],
        "steps": steps,
        "status": "pending_approval",
        "approved": False,
        "trip_plan": trip_plan,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_runs.insert_one(run_doc)
    conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
    await db.conversations.update_one(
        {"user_id": req.user_id},
        {"$set": {
            "messages": conversation,
            "event_active": True,
            "event_active": False,
            "event_source_question_asked": bool((previous or {}).get("event_source_question_asked")),
            "event_traveler_question_asked": bool((previous or {}).get("event_traveler_question_asked")),
            "event_details": trip_plan["details"],
            "explainability": _stored_explanations(trip_plan),
        }},
        upsert=True,
    )
    return {
        "mode": "conversation",
        "run_id": run_id,
        "request": combined_user_text,
        "intent": "event_travel",
        "steps": steps,
        "trip_plan": trip_plan,
        "reply": reply,
        "conversation": conversation,
        "missing": [],
        "ready_to_book": True,
        "disclaimer": "Demo data — all prices and bookings are simulated.",
    }


async def _conversational_chat(req: ChatRequest, message: str):
    conversation = []
    for item in req.conversation[-30:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant"):
            content = sanitize_user_input(str(item.get("content", "")))
            if content:
                conversation.append({"role": item["role"], "content": content})
    if req.reset:
        conversation = []

    previous = None if req.reset else await db.conversations.find_one(
        {"user_id": req.user_id}, {"_id": 0}
    )
    explanation = _why_reply(message, (previous or {}).get("explainability", {}))
    if explanation is not None:
        conversation.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": explanation},
        ])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {"messages": conversation}},
            upsert=True,
        )
        return {
            "mode": "conversation",
            "reply": explanation,
            "conversation": conversation,
            "explanation_only": True,
        }
    prior_details = (previous or {}).get("trip_details", {})
    questions_asked = int((previous or {}).get("questions_asked", 0))
    prior_question = next(
        (item["content"] for item in reversed(conversation) if item["role"] == "assistant"),
        "",
    ).lower()
    user_messages = [item["content"] for item in conversation if item["role"] == "user"]
    user_messages.append(message)
    combined_user_text = "\n".join(user_messages)
    parsed = extract_trip_details(combined_user_text)
    if parsed.get("travelers") is None and "how many travelers" in prior_question:
        parsed["travelers"] = _standalone_traveler_count(message)
    details = {**prior_details, **{key: value for key, value in parsed.items() if value is not None}}

    event_previous = None if req.reset else await db.conversations.find_one(
        {"user_id": req.user_id}, {"_id": 0}
    )
    previous_event_details = (event_previous or {}).get("event_details", {})
    pending_event_source = bool(
        (event_previous or {}).get("event_active")
        and (
            not previous_event_details.get("source")
            or (event_previous or {}).get("event_traveler_question_asked")
        )
    )
    current_event_tool = _event_tool_from_text(message)
    event_tool = current_event_tool or (
        previous_event_details.get("event_tool") if pending_event_source else None
    )
    event_source = _event_source_city(combined_user_text)
    event_related = bool(
        event_tool
        and (
            pending_event_source
            or (
                current_event_tool
                and (
                    event_source
                    or re.search(r"\b(travel|trip|visit|go to|getting to|traveling|travelling)\b", message, re.IGNORECASE)
                    or len(_event_cities(message)) >= 1
                )
            )
        )
    )
    if event_related:
        return await _conversational_event_plan(
            req,
            message,
            conversation,
            event_previous,
            combined_user_text,
            parsed,
            event_tool,
        )

    current_city = agent_parser._extract_city(message)
    if current_city and (
        "which city are you travelling from" in prior_question
        or "which city are you starting from" in prior_question
    ):
        details["source"] = current_city
    elif current_city and "where would you like to go" in prior_question:
        details["destination"] = current_city
    elif "how many people are travelling" in prior_question:
        count_match = re.search(r"\b(\d+|one|two|three|four|five|six|seven|eight)\b", message, re.IGNORECASE)
        if count_match:
            value = count_match.group(1).lower()
            details["travelers"] = int(value) if value.isdigit() else {
                "one": 1, "two": 2, "three": 3, "four": 4,
                "five": 5, "six": 6, "seven": 7, "eight": 8,
            }[value]
    elif "for how many days" in prior_question:
        day_count = _extract_requested_days(message)
        bare_count = re.fullmatch(r"\s*(\d+|one|two|three|four|five|six|seven|eight)\s*[.!]?\s*", message, re.IGNORECASE)
        if day_count is None and bare_count:
            value = bare_count.group(1).lower()
            day_count = int(value) if value.isdigit() else {
                "one": 1, "two": 2, "three": 3, "four": 4,
                "five": 5, "six": 6, "seven": 7, "eight": 8,
            }[value]
        if day_count:
            details["days"] = day_count
    elif "total budget" in prior_question:
        amount_match = re.search(r"\d[\d,]*", message)
        if amount_match:
            details["budget"] = float(amount_match.group(0).replace(",", ""))
    elif "what interests should i include" in prior_question:
        details["interests"] = message

    more_days = re.search(r"\b(?:add|extend)\s+(?:one|1)\s+more\s+night\b", message, re.IGNORECASE)
    if more_days and prior_details.get("nights"):
        details["nights"] = prior_details["nights"] + 1
    if re.search(r"\b(no preference|any is fine)\b", message, re.IGNORECASE):
        details["preference"] = details.get("preference") or "comfort"
    if re.search(r"\b(make it cheaper|lower cost|spend less)\b", message, re.IGNORECASE):
        details["preference"] = "budget"
    if re.search(r"\b(?:add|extend)\s+(?:one|1)\s+more\s+night\b", message, re.IGNORECASE):
        more_days = True
    if prior_question and re.fullmatch(r"\s*(?:yes|yeah|ok|okay|any|anything|sure)\s*[.!]?\s*", message, re.IGNORECASE):
        if "starting from" in prior_question and not details.get("source"):
            details["source"] = "Delhi"
        if ("going" in prior_question or "like to go" in prior_question) and not details.get("destination"):
            details["destination"] = "Goa"
        if "what date" in prior_question and not details.get("start_date"):
            details["start_date"] = (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat()

    destination_plan_active = bool((previous or {}).get("destination_plan_active"))
    destination_request = bool(re.search(
        r"\b(trip|travel|holiday|vacation|itinerary|destination|plan)\b",
        message,
        re.IGNORECASE,
    ))
    theme_request = bool(
        re.search(r"\b(beach|hills|culture|spiritual|adventure|wildlife|food|nature)\b", message, re.IGNORECASE)
        and re.search(r"\b(from|under|within|budget|in|trip|travel|plan)\b", message, re.IGNORECASE)
    )
    if destination_plan_active or destination_request or theme_request:
        plan_base = (previous or {}).get("destination_plan_details", {}) if destination_plan_active else {}
        plan_details = extract_destination_request(message, plan_base)
        if destination_plan_active and (
            "starting from" in prior_question or "starting from" in prior_question
            or "which city are you starting" in prior_question
        ):
            city_answer = agent_parser._extract_city(message)
            if city_answer:
                plan_details["source"] = city_answer
        if destination_plan_active and re.fullmatch(r"\s*(?:yes|yeah|yep|ok|okay|any|sure)\s*[.!]?\s*", message, re.IGNORECASE):
            if "starting from" in prior_question:
                plan_details["source"] = plan_details.get("source") or "Delhi"
            elif "what date" in prior_question:
                plan_details["start_date"] = plan_details.get("start_date") or (
                    datetime.now(timezone.utc).date() + timedelta(days=7)
                ).isoformat()
        if re.search(r"\b(make it cheaper|lower cost|spend less|cheaper)\b", message, re.IGNORECASE):
            plan_details["preference"] = "budget"
        if re.search(r"\b(show|make)\s+premium\b", message, re.IGNORECASE):
            plan_details["preference"] = "premium"
        if re.search(r"\b(?:add|extend)\s+(?:one|1)\s+more\s+night\b", message, re.IGNORECASE):
            plan_details["nights"] = int(plan_details.get("nights") or 1) + 1
        plan_result = build_destination_trip(plan_details, message)
        plan_reply = plan_result.pop("question", None)
        asked_follow_up = bool(plan_reply)
        if plan_reply is None:
            if plan_result.get("error"):
                plan_reply = plan_result["error"]
            elif plan_result.get("kind") == "destination_suggestions":
                plan_reply = (
                    f"I found {len(plan_result['suggestions'])} in-season {plan_details.get('theme', 'trip')} "
                    "destinations. Choose one in the panel."
                )
            else:
                plan_reply = "I built your destination trip plan with simulated tool results. Review the route, stay, itinerary, and costs in the panel."
        conversation.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": plan_reply},
        ])
        run_id = None
        steps = []
        if plan_result.get("kind") == "destination_trip":
            for direction in ("outbound", "return"):
                leg = next(
                    (
                        item for item in plan_result.get("route_legs", [])
                        if item.get("direction") == direction
                        and item.get("type") == "transport"
                    ),
                    None,
                )
                if leg:
                    step_params = {
                        "source": leg["from"],
                        "destination": leg["to"],
                        "date": plan_result["details"]["start_date"] if direction == "outbound"
                        else plan_result["details"]["return_date"],
                        "passengers": plan_result["details"]["travelers"],
                    }
                    steps.append({"tool": leg["mode"], "parameters": step_params, "status": "pending"})
            steps.append({
                "tool": "trip_planner",
                "parameters": {
                    "source": plan_result["details"]["source"],
                    "destination": plan_result["details"]["destination"],
                    "start_date": plan_result["details"]["start_date"],
                    "nights": plan_result["details"]["nights"],
                    "travelers": plan_result["details"]["travelers"],
                    "budget": plan_result["details"]["budget"],
                    "preference": plan_result["details"]["preference"],
                    "interests": ", ".join(plan_result["details"]["interests"]),
                },
                "status": "pending",
            })
            run_id = str(uuid4())
            await db.agent_runs.insert_one({
                "run_id": run_id,
                "user_id": req.user_id,
                "request": combined_user_text,
                "intents": [step["tool"] for step in steps],
                "steps": steps,
                "status": "pending_approval",
                "approved": False,
                "trip_plan": plan_result,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {
                "messages": conversation,
                "trip_details": plan_result.get("details", plan_details),
                "destination_plan_details": plan_result.get("details", plan_details),
                "destination_plan_active": True,
                "trip_active": True,
                "questions_asked": questions_asked + int(asked_follow_up),
                "explainability": _stored_explanations(plan_result),
            }},
            upsert=True,
        )
        return {
            "mode": "conversation",
            "run_id": run_id,
            "request": combined_user_text,
            "intent": "trip",
            "intents": [step["tool"] for step in steps],
            "params": plan_result.get("details", plan_details),
            "steps": steps,
            "trip_plan": plan_result if plan_result.get("kind") else None,
            "reply": plan_reply,
            "conversation": conversation,
            "missing": [],
            "ready_to_book": bool(run_id),
            "disclaimer": "Demo data — all prices and bookings are simulated.",
        }

    turn_messages = [*conversation, {"role": "user", "content": message}]
    llm_result = await conversational_turn(turn_messages, details)
    llm_details = llm_result.get("details") if isinstance(llm_result, dict) else None
    if isinstance(llm_details, dict):
        for key in (
            "source", "destination", "start_date", "nights", "travelers",
            "budget", "preference", "interests",
        ):
            value = llm_details.get(key)
            if value is not None and value != "":
                details[key] = value
    if more_days and prior_details.get("nights"):
        details["nights"] = prior_details["nights"] + 1
    if re.search(r"\b(make it cheaper|lower cost|spend less)\b", message, re.IGNORECASE):
        details["preference"] = "budget"
    for key in ("source", "destination"):
        value = details.get(key)
        if isinstance(value, str):
            details[key] = agent_parser.CITY_ALIASES.get(value.strip().lower(), value.strip().title())
    if details.get("start_date"):
        try:
            details["start_date"] = datetime.fromisoformat(
                str(details["start_date"])
            ).date().isoformat()
        except ValueError:
            details["start_date"] = None
    if details.get("preference"):
        details["preference"] = str(details["preference"]).lower()
        if details["preference"] not in ("budget", "comfort", "luxury", "all"):
            details["preference"] = None
    if re.search(r"\b(?:cheap|cheapest|hostel|budget-friendly|low-cost)\b", combined_user_text, re.IGNORECASE):
        details["preference"] = "budget"
    for key in ("nights", "travelers", "budget"):
        if details.get(key) is not None:
            try:
                details[key] = int(details[key]) if key != "budget" else float(details[key])
            except (TypeError, ValueError):
                details[key] = None

    sections, standalone = _requested_conversation_sections(combined_user_text)
    if standalone:
        vague_answer = bool(re.fullmatch(
            r"\s*(?:yes|yeah|yep|ok|okay|sure|fine|any|whatever)[.!]?\s*",
            message,
            re.IGNORECASE,
        ))
        if vague_answer:
            if not details.get("city") and "which city should i search" in prior_question:
                details["city"] = "Delhi"
            if (
                "hotel" in sections
                and not details.get("start_date")
                and "hotel check-in date" in prior_question
            ):
                details["start_date"] = (
                    datetime.now(timezone.utc).date() + timedelta(days=7)
                ).isoformat()
            if (
                "local_transport" in sections
                and not details.get("days")
                and "for how many days" in prior_question
            ):
                details["days"] = 3
        details["city"] = (
            details.get("city")
            or details.get("destination")
            or agent_parser._extract_city(combined_user_text)
        )
        if details.get("city"):
            details["destination"] = details["city"]
        details["days"] = _extract_requested_days(combined_user_text) or details.get("days")
        details.setdefault("nights", 3)
        if "hotel" in sections and "local_transport" in sections and not details.get("days"):
            details["days"] = details["nights"] + 1

    trip_active = any(
        re.search(r"\b(trip|travel|vacation|holiday|itinerary|plan(?:ning)? a)\b", text, re.IGNORECASE)
        for text in user_messages
    ) or bool(parsed.get("source") or parsed.get("destination")) or bool(
        re.search(r"\b(beach|hills|culture|spiritual|adventure|wildlife|food|nature)\b", message, re.IGNORECASE)
        and re.search(r"\b(from|under|within|budget|in|trip|travel|plan)\b", message, re.IGNORECASE)
    ) or bool(previous and previous.get("trip_active")) or standalone
    supported = re.search(
        r"\b(flight|train|bus|hotel|cricket|concert|budget|trip|travel|booking|book|local transport)\b",
        message,
        re.IGNORECASE,
    )
    if not trip_active:
        if not supported:
            reply = "I can only help with travel, trips, budgets, and simulated bookings for flights, trains, buses, hotels, cricket, or concerts."
        else:
            reply = "I can help with simulated flights, trains, buses, hotels, cricket, concerts, trip planning, and budgeting. Live inventory is not available."
        conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {"messages": conversation, "trip_details": {}, "trip_active": False}},
            upsert=True,
        )
        return {"mode": "conversation", "reply": reply, "conversation": conversation, "trip_plan": None}

    details.setdefault("nights", 3)
    details.setdefault("travelers", 1)
    details.setdefault("preference", "all")
    details.setdefault("interests", "local highlights")
    details.setdefault("budget", None)
    question = _conversation_question(details, sections, standalone) if standalone or questions_asked < 2 else None
    group_size_missing = _group_size_missing(combined_user_text, parsed.get("travelers"))
    group_question_asked = bool((previous or {}).get("group_size_question_asked"))
    if (
        not standalone
        and
        question is None
        and group_size_missing
        and not group_question_asked
        and questions_asked < 2
    ):
        question = "How many travelers should I include?"
    if questions_asked >= 2 and not standalone:
        details.setdefault("source", "Delhi")
        details.setdefault("destination", "Goa")
        details.setdefault(
            "start_date",
            (datetime.now(timezone.utc).date() + timedelta(days=7)).isoformat(),
        )
    if question:
        questions_asked += 1
        reply = question
        conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {
                "messages": conversation,
                "trip_details": details,
                "trip_active": True,
                "questions_asked": questions_asked,
                "group_size_question_asked": group_question_asked or "how many travelers" in question.lower(),
            }},
            upsert=True,
        )
        return {
            "mode": "conversation",
            "reply": reply,
            "conversation": conversation,
            "trip_details": details,
            "trip_plan": None,
        }

    if standalone:
        standalone_steps = []
        tool_results = {}
        if "hotel" in sections:
            standalone_steps.append({
                "tool": "hotel",
                "parameters": {
                    "city": details["city"],
                    "check_in": details["start_date"],
                    "nights": details["nights"],
                    "guests": details["travelers"],
                },
            })
        if "local_transport" in sections:
            standalone_steps.append({
                "tool": "local_transport",
                "parameters": {"city": details["city"], "days": details["days"]},
            })
        for step in standalone_steps:
            tool_results[step["tool"]] = run_registered_tool(step["tool"], step["parameters"], {})
        options = {}
        tradeoffs = {}
        if "hotel" in sections:
            hotel_options = _tier_options(
                tool_results["hotel"]["results"], "price_per_night", "rating"
            )
            options["hotel"], tradeoffs["hotel"] = _explain_options(
                hotel_options,
                "hotel",
                preference=details.get("preference"),
                budget=details.get("budget"),
                quantity=details["travelers"],
                nights=details["nights"],
            )
        if "local_transport" in sections:
            options["local_transport"], tradeoffs["local_transport"] = _explain_options(
                tool_results["local_transport"]["results"],
                "local_transport",
                quantity=details["days"],
            )
        trip_plan = {
            "kind": "tool_results",
            "details": details,
            "sections": sections,
            "options": options,
            "tradeoffs": tradeoffs,
            "local_transport_days": details.get("days"),
        }
        if "local_transport" in tool_results:
            trip_plan["local_transport"] = tool_results["local_transport"]["results"]
        reply_parts = []
        if "hotel" in sections:
            reply_parts.append("3 hotel options")
        if "local_transport" in sections:
            reply_parts.append("local transport estimates")
        reply = f"I found {' and '.join(reply_parts)} for {details['city']}. Check the panel."
        run_id = str(uuid4())
        run_doc = {
            "run_id": run_id,
            "user_id": req.user_id,
            "request": combined_user_text,
            "intents": [step["tool"] for step in standalone_steps],
            "steps": standalone_steps,
            "status": "pending_approval",
            "approved": False,
            "trip_plan": trip_plan,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.agent_runs.insert_one(run_doc)
        conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
        await db.conversations.update_one(
            {"user_id": req.user_id},
            {"$set": {
                "messages": conversation,
                "trip_details": details,
                "trip_active": True,
                "requested_sections": sections,
                "explainability": _stored_explanations(trip_plan),
            }},
            upsert=True,
        )
        return {
            "mode": "conversation",
            "run_id": run_id,
            "request": combined_user_text,
            "intent": "trip",
            "intents": run_doc["intents"],
            "params": details,
            "steps": standalone_steps,
            "trip_plan": trip_plan,
            "reply": reply,
            "conversation": conversation,
            "missing": [],
            "ready_to_book": True,
            "disclaimer": "Demo data — all prices and bookings are simulated.",
        }

    prior_tier_filter = (previous or {}).get("hotel_tier_filter")
    hotel_tier_filter = prior_tier_filter
    if re.search(r"\bpremium\s+hotels?\s+only\b", message, re.IGNORECASE):
        hotel_tier_filter = "Premium"
    elif re.search(r"\b(?:all|show all)\s+(?:hotel\s+)?tiers\b", message, re.IGNORECASE):
        hotel_tier_filter = None
    if re.search(r"\bmake it cheaper\b", message, re.IGNORECASE):
        details["preference"] = "budget"

    steps = validate_plan(_trip_steps(details, sections))
    tool_results = {}
    for step in steps:
        tool_results[step["tool"]] = run_registered_tool(step["tool"], step["parameters"], {})
    trip_plan = _build_trip_preview(details, sections, tool_results)
    trip_plan["hotel_tier_filter"] = hotel_tier_filter
    section_names = {
        "flight": "Flights",
        "train": "Trains",
        "bus": "Buses",
        "hotel": "Hotels",
        "local_transport": "Local transport estimates",
    }
    includes_transport = any(tool in sections for tool in ("flight", "train", "bus"))
    shown_sections = ", ".join(section_names[section] for section in sections)
    reply = (
        f"I found options for {shown_sections}. Check the panel"
        f"{' to compare prices and times' if includes_transport else ''}."
    )
    if hotel_tier_filter:
        reply = "Showing Premium hotel options in the panel. Tell me if you want a different tier."

    run_id = str(uuid4())
    run_doc = {
        "run_id": run_id,
        "user_id": req.user_id,
        "request": combined_user_text,
        "intents": [step["tool"] for step in steps],
        "steps": steps,
        "status": "pending_approval",
        "approved": False,
        "trip_plan": trip_plan,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_runs.insert_one(run_doc)
    conversation.extend([{"role": "user", "content": message}, {"role": "assistant", "content": reply}])
    await db.conversations.update_one(
        {"user_id": req.user_id},
        {"$set": {
            "messages": conversation,
            "trip_details": details,
            "trip_active": True,
            "questions_asked": questions_asked,
            "hotel_tier_filter": hotel_tier_filter,
            "explainability": _stored_explanations(trip_plan),
            "group_size_question_asked": group_question_asked or "how many travelers" in prior_question,
        }},
        upsert=True,
    )
    return {
        "mode": "conversation",
        "run_id": run_id,
        "request": combined_user_text,
        "intent": "trip",
        "intents": run_doc["intents"],
        "params": details,
        "steps": steps,
        "trip_plan": trip_plan,
        "reply": reply,
        "conversation": conversation,
        "missing": [],
        "ready_to_book": True,
        "disclaimer": "Demo data — all prices and bookings are simulated.",
    }


# ------------- Endpoints -------------
@api.get("/")
async def root():
    return {"service": "AURA", "status": "running", "disclaimer": "All bookings are simulated / demo."}


@api.get("/meta")
async def meta():
    return {
        "supported_cities": sorted(set(SUPPORTED_CITIES) | set(GEN_CITIES.keys())),
        "tools": tool_descriptions(),
        "booking_types": ["movie", "hotel", "flight", "train", "bus", "cricket", "concert"],
        "disclaimer": "Demo data — all bookings are simulated.",
    }


@api.post("/auth/signup")
async def signup(req: SignupRequest):
    if not AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Authentication is disabled.")
    password_bytes = req.password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(status_code=422, detail="Password cannot exceed 72 UTF-8 bytes.")
    email = str(req.email).strip().lower()
    if await db.users.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = {
        "_id": str(uuid4()),
        "name": req.name,
        "email": email,
        "password_hash": bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from None
    return _auth_response(user)


@api.post("/auth/login")
async def login(req: LoginRequest):
    if not AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Authentication is disabled.")
    user = await db.users.find_one({"email": str(req.email).strip().lower()})
    if not user or not bcrypt.checkpw(
        req.password.encode("utf-8"), user["password_hash"].encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _auth_response(user)


@api.get("/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    if not AUTH_ENABLED:
        return {**DEFAULT_USER, "auth_enabled": False}
    return current_user


@api.post("/chat")
async def chat(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    """Create and validate a JSON task plan without executing its tools."""
    _apply_authenticated_owner(req, current_user)
    message = sanitize_user_input(req.message)
    if not message:
        raise HTTPException(status_code=400, detail="Empty message")
    if req.mode == "conversation":
        return await _conversational_chat(req, message)

    try:
        parsed = await create_task_plan(message, req.tool)
        steps = validate_plan(parsed.get("steps"))
    except MissingToolParameters as exc:
        question = missing_parameter_question(exc.tool, exc.parameter)
        steps = parsed.get("steps", []) if "parsed" in locals() else []
        steps = [
            {**step, "status": "pending"}
            for step in steps
            if isinstance(step, dict)
        ]
        intent = steps[0]["tool"] if steps else "unknown"
        run_id = str(uuid4())
        await db.agent_runs.insert_one({
            "run_id": run_id,
            "user_id": req.user_id,
            "request": message,
            "intents": parsed.get("intents", []) if "parsed" in locals() else [],
            "steps": steps,
            "status": "awaiting_input",
            "follow_up_question": question,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "run_id": run_id,
            "request": message,
            "intent": intent,
            "intents": parsed.get("intents", []) if "parsed" in locals() else [],
            "params": steps[0].get("parameters", {}) if steps else {},
            "steps": steps,
            "plan": build_plan(intent),
            "missing": [question],
            "question": question,
            "parser_source": parsed.get("source", "fallback") if "parsed" in locals() else "fallback",
            "ready_to_search": False,
            "disclaimer": "Demo data — all tools are simulated.",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    intents = list(dict.fromkeys(step["tool"] for step in steps))
    intent = intents[0] if len(intents) == 1 else "trip"
    params = steps[0]["parameters"]
    missing = []
    question = None
    for step in steps:
        try:
            validate_plan([step])
        except MissingToolParameters as exc:
            question = missing_parameter_question(exc.tool, exc.parameter)
            missing = [question]
            break

    if missing:
        status = "awaiting_input"
    else:
        status = "pending_approval"
    run_id = str(uuid4())
    run_doc = {
        "run_id": run_id,
        "user_id": req.user_id,
        "request": message,
        "intents": intents,
        "steps": steps,
        "status": status,
        "approved": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if question:
        run_doc["follow_up_question"] = question
    await db.agent_runs.insert_one(run_doc)

    return {
        "run_id": run_id,
        "request": message,
        "intent": intent,
        "intents": intents,
        "params": params,
        "steps": steps,
        "plan": build_plan(intent if intent in ("movie", "hotel", "flight") else "unknown"),
        "missing": missing,
        "question": question,
        "parser_source": parsed.get("source", "fallback"),
        "ready_to_search": not missing,
        "disclaimer": "Demo data — all tools are simulated.",
    }


@api.post("/search")
async def search(req: SearchRequest, _current_user: dict = Depends(get_current_user)):
    """Run the appropriate search tool."""
    intent = req.intent
    params = req.params or {}
    if intent not in TOOL_REGISTRY:
        raise HTTPException(status_code=400, detail="Unsupported intent")
    result = _annotate_tool_result(
        intent,
        run_registered_tool(intent, params, {}),
        params,
    )
    results = result.get("results", [])
    return {"intent": intent, "count": len(results), "results": results}


@api.post("/runs/{run_id}/approve")
async def approve_run(
    run_id: str,
    req: RunRequest,
    current_user: dict = Depends(get_current_user),
):
    """Record the user's explicit approval before any planned tool can run."""
    _apply_authenticated_owner(req, current_user)
    result = await db.agent_runs.update_one(
        {
            "run_id": run_id,
            "user_id": req.user_id,
            "status": "pending_approval",
            "approved": False,
        },
        {
            "$set": {
                "approved": True,
                "status": "running",
                "approved_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if result.matched_count != 1:
        raise HTTPException(status_code=409, detail="This plan is not awaiting approval.")
    return {"run_id": run_id, "approved": True}


@api.post("/runs/{run_id}/steps")
async def execute_step(
    run_id: str,
    req: ExecuteStepRequest,
    current_user: dict = Depends(get_current_user),
):
    """Execute exactly the next approved step through the mock-tool allow-list."""
    _apply_authenticated_owner(req, current_user)
    run = await db.agent_runs.find_one(
        {"run_id": run_id, "user_id": req.user_id}, {"_id": 0}
    )
    if not run:
        raise HTTPException(status_code=404, detail="Plan not found.")
    if not run.get("approved"):
        raise HTTPException(status_code=403, detail="Approve this plan before running tools.")
    steps = run.get("steps", [])
    if req.index >= len(steps):
        raise HTTPException(status_code=400, detail="Step is outside this plan.")
    step = steps[req.index]
    if step.get("status") != "pending":
        raise HTTPException(status_code=409, detail="This step is not pending.")
    if req.index and steps[req.index - 1].get("status") != "done":
        raise HTTPException(status_code=409, detail="The previous step has not completed.")

    step_path = f"steps.{req.index}"
    claimed = await db.agent_runs.update_one(
        {
            "run_id": run_id,
            "user_id": req.user_id,
            "approved": True,
            f"{step_path}.status": "pending",
        },
        {
            "$set": {
                f"{step_path}.status": "running",
                f"{step_path}.started_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    if claimed.matched_count != 1:
        raise HTTPException(status_code=409, detail="This step is already running.")

    previous = steps[req.index - 1].get("result", {}) if req.index else {}
    try:
        parameters = resolve_parameters(step["parameters"], previous)
        trip_details = (run.get("trip_plan") or {}).get("details", {})
        result = _annotate_tool_result(
            step["tool"],
            run_registered_tool(step["tool"], parameters, previous),
            parameters,
            preference=trip_details.get("preference"),
            budget=trip_details.get("budget"),
        )
    except Exception as exc:
        logger.exception("Mock tool step failed: %s", step.get("tool"))
        await db.agent_runs.update_one(
            {"run_id": run_id, "user_id": req.user_id},
            {
                "$set": {
                    f"{step_path}.status": "failed",
                    f"{step_path}.error": "The mock tool could not complete this step.",
                    f"{step_path}.finished_at": datetime.now(timezone.utc).isoformat(),
                    "status": "failed",
                }
            },
        )
        raise HTTPException(status_code=500, detail="The mock tool failed. Remaining steps were stopped.") from exc

    finished_at = datetime.now(timezone.utc).isoformat()
    next_status = "complete" if req.index == len(steps) - 1 else "running"
    await db.agent_runs.update_one(
        {"run_id": run_id, "user_id": req.user_id},
        {
            "$set": {
                f"{step_path}.status": "done",
                f"{step_path}.result": result,
                f"{step_path}.finished_at": finished_at,
                "status": next_status,
            }
        },
    )
    return {"index": req.index, "tool": step["tool"], "status": "done", "result": result}


@api.get("/history/{user_id}")
async def history(user_id: str, current_user: dict = Depends(get_current_user)):
    """Load simulated bookings and plans belonging to the authenticated user."""
    owner_id = current_user.get("id", user_id)
    runs = await db.agent_runs.find({"user_id": owner_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    bookings = await db.bookings.find({"user_id": owner_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"runs": runs, "bookings": bookings}


@api.post("/confirm")
async def confirm(req: ConfirmRequest, _current_user: dict = Depends(get_current_user)):
    """Preview the booking — compute total price before user confirms."""
    option = get_option_by_id(req.intent, req.option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    nights = req.nights if req.intent == "hotel" else 1
    amount = price_booking(
        req.intent, option, req.quantity, nights, req.rooms,
        req.promo_code, req.insurance,
    )
    return {
        "intent": req.intent,
        "option": option,
        "quantity": req.quantity,
        "rooms": req.rooms if req.intent == "hotel" else None,
        "nights": nights,
        "amount": amount,
        "fare_breakdown": amount["breakdown"],
        "needs_confirmation": True,
        "disclaimer": "Demo data — all bookings are simulated.",
    }


@api.post("/confirm/plan")
async def confirm_plan(req: ConfirmPlanRequest, _current_user: dict = Depends(get_current_user)):
    """Price every booking in a plan and aggregate its quote on the backend."""
    priced_items = []
    for item in req.items:
        option = get_option_by_id(item.intent, item.option_id)
        if not option:
            raise HTTPException(status_code=404, detail=f"Option not found: {item.option_id}")
        nights = item.nights if item.intent == "hotel" else 1
        amount = price_booking(
            item.intent, option, item.quantity, nights, item.rooms,
            item.promo_code, item.insurance,
        )
        priced_items.append({
            "intent": item.intent,
            "option": option,
            "quantity": item.quantity,
            "nights": nights,
            "rooms": item.rooms if item.intent == "hotel" else 1,
            "preview": {"intent": item.intent, "option": option, "amount": amount},
        })
    amount_keys = ("subtotal", "fees", "discount", "tax", "total")
    aggregate = {key: round(sum(item["preview"]["amount"][key] for item in priced_items), 2) for key in amount_keys}
    aggregate["per_person"] = round(aggregate["total"] / req.items[0].quantity, 2)
    rates = {item["preview"]["amount"]["gst_rate"] for item in priced_items}
    aggregate["gst_rate"] = rates.pop() if len(rates) == 1 else None
    aggregate["currency"] = "INR"
    aggregate["breakdown"] = [
        {**line, "label": f"{item['intent'].title()}: {line['label']}"}
        for item in priced_items
        for line in item["preview"]["amount"]["breakdown"]
    ]
    aggregate["promo_valid"] = all(item["preview"]["amount"]["promo_valid"] for item in priced_items)
    aggregate["promo_code"] = next(
        (item["preview"]["amount"]["promo_code"] for item in priced_items if item["preview"]["amount"]["promo_code"]),
        None,
    )
    aggregate["insurance"] = any(item["preview"]["amount"]["insurance"] for item in priced_items)
    return {"items": priced_items, "amount": aggregate}


@api.post("/book")
async def book(req: BookRequest, current_user: dict = Depends(get_current_user)):
    """Create a mock booking only after explicit user confirmation."""
    _apply_authenticated_owner(req, current_user)
    if not req.confirmed:
        raise HTTPException(
            status_code=400, detail="User confirmation required to create booking")
    if req.run_id:
        run = await db.agent_runs.find_one(
            {"run_id": req.run_id, "user_id": req.user_id}, {"_id": 0}
        )
        if not run or not run.get("approved") or run.get("status") != "complete":
            raise HTTPException(
                status_code=403,
                detail="Complete and approve the associated plan before booking.",
            )
    option = get_option_by_id(req.intent, req.option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    nights = req.nights if req.intent == "hotel" else 1
    if len(req.passengers) != req.quantity:
        raise HTTPException(status_code=422, detail="Passenger count must match the number of travelers.")
    amount = price_booking(
        req.intent, option, req.quantity, nights, req.rooms,
        req.promo_code, req.insurance,
    )
    extra = {"nights": nights, "rooms": req.rooms} if req.intent == "hotel" else {}
    if req.intent == "movie" and req.seats:
        extra["seats"] = req.seats

    booking = create_mock_booking(
        req.intent, option, req.quantity, amount, extra)
    booking.update({
        "pnr": f"AURA{secrets.token_hex(3).upper()}" if req.intent in {"flight", "train"} else None,
        "transaction_id": f"TXN{''.join(secrets.choice('0123456789') for _ in range(10))}",
        "payment_method": req.payment_method,
        "payment_timestamp": datetime.now(timezone.utc).isoformat(),
        "passengers": [passenger.model_dump() for passenger in req.passengers],
        "contact": req.contact.model_dump(),
        "fare_breakdown": amount["breakdown"],
        "cancellation_policy": "Simulated bookings cannot be cancelled or exchanged.",
        "simulated": True,
    })
    verified = verify_booking(booking)
    booking["verified"] = verified

    doc = {
        **booking,
        "user_request": req.user_request,
        "user_id": req.user_id,
        "run_id": req.run_id,
    }
    try:
        await db.bookings.insert_one(doc)
    except Exception as e:
        logger.exception("Could not persist simulated booking.")
        raise HTTPException(status_code=503, detail="Could not save the simulated booking to history.") from e

    await _log_step(booking["booking_id"], "Mock booking created", "done", req.user_id)
    await _log_step(
        booking["booking_id"],
        "Booking verified",
        "done" if verified else "failed",
        req.user_id,
    )
    if req.run_id:
        await db.agent_runs.update_one(
            {"run_id": req.run_id, "user_id": req.user_id},
            {
                "$set": {
                    "booking": {
                        "booking_id": booking["booking_id"],
                        "status": booking["status"],
                        "verified": verified,
                        "simulated": True,
                    },
                    "booking_status": "done" if verified else "failed",
                }
            },
        )

    return booking


@api.get("/booking/{booking_id}")
async def get_booking(
    booking_id: str,
    current_user: dict = Depends(get_current_user),
):
    doc = await db.bookings.find_one(
        {"booking_id": booking_id, "user_id": current_user.get("id")},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return doc


@api.get("/bookings")
async def list_bookings(
    limit: int = 50,
    user_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    query = {"user_id": current_user.get("id", user_id)}
    docs = await db.bookings.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"count": len(docs), "bookings": docs}


# Mount router + CORS
app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def ensure_user_email_index():
    global db, using_memory_fallback
    if not AUTH_ENABLED:
        logger.warning("AUTH_ENABLED=false - login is disabled")
        try:
            await asyncio.wait_for(client.admin.command("ping"), timeout=2)
        except Exception:
            logger.warning("MongoDB unavailable; using in-memory storage until restart.")
            db = InMemoryDatabase()
            using_memory_fallback = True
            return
    await db.users.create_index("email", unique=True)


@app.on_event("shutdown")
async def shutdown_db():
    client.close()
