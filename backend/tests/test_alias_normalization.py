"""Iteration 4: verify CITY_ALIASES normalization is applied to LLM output in parse_request."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend/.env read
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"


def _chat(msg: str) -> dict:
    r = requests.post(f"{API}/chat", json={"message": msg}, timeout=60)
    assert r.status_code == 200, f"status={r.status_code} body={r.text}"
    return r.json()


# --- Targeted alias normalization tests ---

def test_bombay_to_panjim_normalized():
    data = _chat("flight from Bombay to Panjim on 10 December")
    p = data.get("params", {})
    assert data.get("intent") == "flight", data
    assert p.get("source") == "Mumbai", p
    assert p.get("destination") == "Goa", p


def test_calcutta_hotel_normalized():
    data = _chat("book a hotel in Calcutta for 2 nights")
    p = data.get("params", {})
    assert data.get("intent") == "hotel", data
    assert p.get("city") == "Kolkata", p


def test_vizag_destination_normalized():
    data = _chat("flight to Vizag from Delhi")
    p = data.get("params", {})
    assert data.get("intent") == "flight", data
    assert p.get("destination") == "Visakhapatnam", p
    assert p.get("source") == "Delhi", p


def test_trivandrum_movie_normalized():
    data = _chat("movie in Trivandrum tomorrow")
    p = data.get("params", {})
    assert data.get("intent") == "movie", data
    assert p.get("city") == "Thiruvananthapuram", p


# --- Regression: canonical city parsing still works ---

def test_regression_delhi_mumbai_canonical():
    data = _chat("flight from Delhi to Mumbai on 20 December")
    p = data.get("params", {})
    assert p.get("source") == "Delhi", p
    assert p.get("destination") == "Mumbai", p


def test_regression_bengaluru_canonical():
    data = _chat("hotel in Bengaluru for 1 night")
    p = data.get("params", {})
    assert p.get("city") == "Bengaluru", p


# --- Regression: generator still produces 5-8 options for Kolkata->Delhi ---

def test_regression_generator_kolkata_delhi_flight():
    r = requests.post(
        f"{API}/search/flight",
        json={"source": "Kolkata", "destination": "Delhi", "date": "2026-10-25", "passengers": 1},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    opts = data.get("options") or data.get("results") or data
    if isinstance(opts, dict):
        opts = opts.get("options") or opts.get("results") or []
    assert 5 <= len(opts) <= 8, f"Expected 5-8 options, got {len(opts)}: keys={list(data.keys()) if isinstance(data,dict) else type(data)}"
    # Exactly one cheapest
    cheapest = [o for o in opts if o.get("is_cheapest")]
    assert len(cheapest) == 1, f"Expected 1 cheapest, got {len(cheapest)}"
