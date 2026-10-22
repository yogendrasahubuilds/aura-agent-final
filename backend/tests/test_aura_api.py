"""Backend regression tests for AURA. Focus on seats support + prior behaviour."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://aura-workflow-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
CHECKOUT_DETAILS = {
    "passengers": [{"name": "Test Traveler", "age": 30, "gender": "Prefer not to say"}],
    "contact": {"email": "traveler@example.test", "phone": "9876543210"},
    "payment_method": "UPI",
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- /chat ----------
def test_chat_movie(session):
    r = session.post(f"{API}/chat", json={"message": "Book 2 tickets for Mirzapur tomorrow evening in Bhilai"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "movie"
    assert d["ready_to_search"] is True
    assert d["missing"] == []
    assert len(d["plan"]) == 8
    assert "disclaimer" in d


def test_chat_hotel(session):
    r = session.post(f"{API}/chat", json={"message": "Book a hotel in Raipur for 2 nights from 15 October for 2 guests"})
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "hotel"
    assert d["ready_to_search"] is True


def test_chat_flight(session):
    r = session.post(f"{API}/chat", json={"message": "Find a flight from Raipur to Delhi on 20 October for 1 passenger"})
    assert r.status_code == 200
    assert r.json()["intent"] == "flight"


# ---------- /search ----------
def test_search_movie(session):
    r = session.post(f"{API}/search", json={"intent": "movie", "params": {"city": "Bhilai"}})
    assert r.status_code == 200
    assert r.json()["count"] >= 1


# ---------- simulated itemized fare preview ----------
def test_confirm_movie_itemized_gst(session):
    r = session.post(f"{API}/confirm", json={"intent": "movie", "option_id": "M001", "quantity": 2})
    assert r.status_code == 200
    d = r.json()
    amt = d["amount"]
    assert amt["gst_rate"] == 18
    assert amt["fees"] > 0
    assert amt["breakdown"][-1]["label"] == "GST (18%)"
    assert round(amt["total"], 2) == round(amt["subtotal"] + amt["fees"] - amt["discount"] + amt["tax"], 2)


# ---------- /book require confirmation ----------
def test_book_requires_confirmation(session):
    r = session.post(f"{API}/book", json={
        "intent": "movie", "option_id": "M001", "quantity": 2, "confirmed": False,
        **{**CHECKOUT_DETAILS, "passengers": [
            {"name": "Test Traveler", "age": 30, "gender": "Prefer not to say"},
            {"name": "Second Traveler", "age": 28, "gender": "Prefer not to say"},
        ]},
    })
    assert r.status_code == 400


# ---------- /book with seats ----------
def test_book_movie_with_seats_and_persist(session):
    seats = ["A1", "A2"]
    r = session.post(f"{API}/book", json={
        "intent": "movie", "option_id": "M001", "quantity": 2,
        "confirmed": True, "seats": seats, "user_request": "TEST_seats",
        **{**CHECKOUT_DETAILS, "passengers": [
            {"name": "Test Traveler", "age": 30, "gender": "Prefer not to say"},
            {"name": "Second Traveler", "age": 28, "gender": "Prefer not to say"},
        ]},
    })
    assert r.status_code == 200
    b = r.json()
    bid = b["booking_id"]
    assert bid.startswith("AURA-MOV-")
    assert b.get("verified") is True
    assert b.get("extra", {}).get("seats") == seats
    assert b["transaction_id"].startswith("TXN")
    assert len(b["transaction_id"]) == 13
    assert b["passengers"][0]["name"] == "Test Traveler"

    # GET verifies persistence
    g = session.get(f"{API}/booking/{bid}")
    assert g.status_code == 200
    gd = g.json()
    assert gd["extra"]["seats"] == seats


# ---------- /book without seats (regression) ----------
def test_book_hotel_prefix(session):
    r = session.post(f"{API}/book", json={
        "intent": "hotel", "option_id": "H001", "quantity": 2, "nights": 2,
        "confirmed": True, "user_request": "TEST_hotel",
        **{**CHECKOUT_DETAILS, "passengers": [
            {"name": "Test Traveler", "age": 30, "gender": "Prefer not to say"},
            {"name": "Second Traveler", "age": 28, "gender": "Prefer not to say"},
        ]},
    })
    assert r.status_code == 200
    assert r.json()["booking_id"].startswith("AURA-HTL-")


def test_book_flight_prefix(session):
    r = session.post(f"{API}/book", json={
        "intent": "flight", "option_id": "F001", "quantity": 1,
        "confirmed": True, "user_request": "TEST_flight",
        **CHECKOUT_DETAILS,
    })
    assert r.status_code == 200
    assert r.json()["booking_id"].startswith("AURA-FLT-")
    assert r.json()["pnr"]


def test_book_bad_option(session):
    r = session.post(f"{API}/book", json={
        "intent": "movie", "option_id": "BAD999", "confirmed": True, **CHECKOUT_DETAILS,
    })
    assert r.status_code == 404


def test_list_bookings(session):
    r = session.get(f"{API}/bookings")
    assert r.status_code == 200
    assert "bookings" in r.json()
