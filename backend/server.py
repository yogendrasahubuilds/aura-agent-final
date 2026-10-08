"""AURA — Autonomous Universal Resource Agent (FastAPI backend).
All bookings are SIMULATED / DEMO."""
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime, timezone
from pathlib import Path
import os
import logging

from agent import parse_request, build_plan, validate_params
from tools import movie_search, hotel_search, flight_search, calculator, get_option_by_id
from booking import create_mock_booking, verify_booking
from data import SUPPORTED_CITIES

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="AURA API", description="Autonomous Universal Resource Agent — Simulated Bookings")
api = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ------------- Models -------------
class ChatRequest(BaseModel):
    message: str


class SearchRequest(BaseModel):
    intent: str
    params: dict


class ConfirmRequest(BaseModel):
    intent: str
    option_id: str
    quantity: int = 1
    nights: int = 1


class BookRequest(BaseModel):
    intent: str
    option_id: str
    quantity: int = 1
    nights: int = 1
    confirmed: bool = False
    user_request: Optional[str] = None
    seats: Optional[List[str]] = None


# ------------- Helpers -------------
async def _log_step(booking_id: Optional[str], step: str, status: str = "done"):
    doc = {
        "booking_id": booking_id,
        "step": step,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.execution_logs.insert_one(doc)
    except Exception as e:
        logger.warning(f"log_step failed: {e}")


def _unit_price(intent: str, option: dict) -> float:
    if intent == "movie":
        return option["price"]
    if intent == "hotel":
        return option["price_per_night"]
    if intent == "flight":
        return option["price"]
    return 0.0


# ------------- Endpoints -------------
@api.get("/")
async def root():
    return {"service": "AURA", "status": "running", "disclaimer": "All bookings are simulated / demo."}


@api.get("/meta")
async def meta():
    return {
        "supported_cities": SUPPORTED_CITIES,
        "booking_types": ["movie", "hotel", "flight"],
        "disclaimer": "Demo data — all bookings are simulated.",
    }


@api.post("/chat")
async def chat(req: ChatRequest):
    """Parse NL request → intent + params + plan + validation."""
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    parsed = await parse_request(req.message)
    intent = parsed.get("intent", "unknown")
    params = parsed.get("params") or {}
    missing = validate_params(intent, params)
    plan = build_plan(intent)

    return {
        "intent": intent,
        "params": params,
        "plan": plan,
        "missing": missing,
        "parser_source": parsed.get("source", "regex"),
        "ready_to_search": intent in ("movie", "hotel", "flight") and not missing,
        "disclaimer": "Demo data — all bookings are simulated.",
    }


@api.post("/search")
async def search(req: SearchRequest):
    """Run the appropriate search tool."""
    intent = req.intent
    params = req.params or {}
    if intent == "movie":
        results = movie_search(**params)
    elif intent == "hotel":
        results = hotel_search(**params)
    elif intent == "flight":
        results = flight_search(**params)
    else:
        raise HTTPException(status_code=400, detail="Unsupported intent")
    return {"intent": intent, "count": len(results), "results": results}


@api.post("/confirm")
async def confirm(req: ConfirmRequest):
    """Preview the booking — compute total price before user confirms."""
    option = get_option_by_id(req.intent, req.option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")
    unit = _unit_price(req.intent, option)
    nights = req.nights if req.intent == "hotel" else 1
    # For hotels, price is per-room per-night (guests don't multiply price).
    pricing_qty = 1 if req.intent == "hotel" else req.quantity
    amount = calculator(unit, pricing_qty, nights)
    return {
        "intent": req.intent,
        "option": option,
        "quantity": req.quantity,
        "nights": nights,
        "amount": amount,
        "needs_confirmation": True,
        "disclaimer": "Demo data — all bookings are simulated.",
    }


@api.post("/book")
async def book(req: BookRequest):
    """Create a mock booking only after explicit user confirmation."""
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="User confirmation required to create booking")
    option = get_option_by_id(req.intent, req.option_id)
    if not option:
        raise HTTPException(status_code=404, detail="Option not found")

    unit = _unit_price(req.intent, option)
    nights = req.nights if req.intent == "hotel" else 1
    pricing_qty = 1 if req.intent == "hotel" else req.quantity
    amount = calculator(unit, pricing_qty, nights)
    extra = {"nights": nights} if req.intent == "hotel" else {}
    if req.intent == "movie" and req.seats:
        extra["seats"] = req.seats

    booking = create_mock_booking(req.intent, option, req.quantity, amount, extra)
    verified = verify_booking(booking)
    booking["verified"] = verified

    doc = {
        **booking,
        "user_request": req.user_request,
    }
    try:
        await db.bookings.insert_one(doc)
    except Exception as e:
        logger.warning(f"persist booking failed: {e}")

    await _log_step(booking["booking_id"], "Mock booking created", "done")
    await _log_step(booking["booking_id"], "Booking verified", "done" if verified else "failed")

    return booking


@api.get("/booking/{booking_id}")
async def get_booking(booking_id: str):
    doc = await db.bookings.find_one({"booking_id": booking_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Booking not found")
    return doc


@api.get("/bookings")
async def list_bookings(limit: int = 50):
    docs = await db.bookings.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
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


@app.on_event("shutdown")
async def shutdown_db():
    client.close()
