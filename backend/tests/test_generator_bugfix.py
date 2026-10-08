"""Tests for the dynamic multi-provider generator bugfix.
Previously, searches for cities not in curated data (e.g. Kolkata) returned 0 results.
Now the generator returns 5-8 comparable options for ANY Indian city/route.
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Bug Fix: Flight (previously 0 results) ----------
@pytest.mark.parametrize("src,dst", [("Kolkata", "Delhi"), ("Chennai", "Goa")])
def test_flight_search_generates_results(session, src, dst):
    r = session.post(f"{API}/search", json={
        "intent": "flight", "params": {"source": src, "destination": dst}
    })
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 5, f"expected >=5 flights for {src}->{dst}, got {d['count']}"
    results = d["results"]
    # Each result has provider
    assert all(r.get("provider") for r in results), "every flight must have provider"
    # Exactly one is_cheapest
    cheapest = [r for r in results if r.get("is_cheapest")]
    assert len(cheapest) == 1, f"expected exactly 1 cheapest, got {len(cheapest)}"
    # save_pct_vs_max present on all
    assert all("save_pct_vs_max" in r for r in results)
    # sorted ascending by price
    prices = [r["price"] for r in results]
    assert prices == sorted(prices), "flights must be sorted ascending by price"
    # cheapest is the first
    assert results[0]["is_cheapest"] is True


# ---------- Bug Fix: Hotel ----------
def test_hotel_search_kolkata(session):
    r = session.post(f"{API}/search", json={"intent": "hotel", "params": {"city": "Kolkata"}})
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 5
    for h in d["results"]:
        assert h.get("provider")
        assert h.get("price_per_night") is not None
    assert sum(1 for h in d["results"] if h.get("is_cheapest")) == 1


# ---------- Bug Fix: Movie ----------
def test_movie_search_patna(session):
    r = session.post(f"{API}/search", json={"intent": "movie", "params": {"city": "Patna"}})
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 5
    for m in d["results"]:
        assert m.get("provider")
    assert sum(1 for m in d["results"] if m.get("is_cheapest")) == 1


# ---------- Regression: curated cities still work ----------
def test_regression_movie_bhilai(session):
    r = session.post(f"{API}/search", json={"intent": "movie", "params": {"city": "Bhilai"}})
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_regression_hotel_raipur(session):
    r = session.post(f"{API}/search", json={"intent": "hotel", "params": {"city": "Raipur"}})
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_regression_flight_raipur_delhi(session):
    r = session.post(f"{API}/search", json={
        "intent": "flight", "params": {"source": "Raipur", "destination": "Delhi"}
    })
    assert r.status_code == 200
    assert r.json()["count"] >= 1


# ---------- Chat parsing new cities + aliases ----------
def test_chat_kolkata_to_delhi(session):
    r = session.post(f"{API}/chat", json={
        "message": "Find a flight from Kolkata to Delhi on 25 October for 1 passenger"
    })
    assert r.status_code == 200
    d = r.json()
    assert d["intent"] == "flight"
    p = d["params"]
    assert p.get("source") == "Kolkata"
    assert p.get("destination") == "Delhi"
    assert p.get("date") and p["date"].endswith("-10-25")
    assert p.get("passengers") == 1


@pytest.mark.parametrize("msg,src,dst", [
    ("Flight from Calcutta to Bombay tomorrow", "Kolkata", "Mumbai"),
    ("flight from Vizag to Trivandrum on 15 November", "Visakhapatnam", "Thiruvananthapuram"),
    ("flight from Bombay to Panjim on 10 December", "Mumbai", "Goa"),
])
def test_chat_aliases(session, msg, src, dst):
    r = session.post(f"{API}/chat", json={"message": msg})
    assert r.status_code == 200
    p = r.json()["params"]
    assert p.get("source") == src, f"expected source={src}, got {p.get('source')}"
    assert p.get("destination") == dst, f"expected destination={dst}, got {p.get('destination')}"


# ---------- Booking generated option end-to-end ----------
def test_book_generated_flight(session):
    s = session.post(f"{API}/search", json={
        "intent": "flight", "params": {"source": "Kolkata", "destination": "Delhi"}
    })
    results = s.json()["results"]
    gen = next((r for r in results if r["id"].startswith("GFL-")), None)
    assert gen is not None, "expected at least one GFL- generated flight"
    oid = gen["id"]
    # confirm
    c = session.post(f"{API}/confirm", json={"intent": "flight", "option_id": oid, "quantity": 1})
    assert c.status_code == 200
    # book
    b = session.post(f"{API}/book", json={
        "intent": "flight", "option_id": oid, "quantity": 1, "confirmed": True,
        "user_request": "TEST_gen_flight",
    })
    assert b.status_code == 200, b.text
    bd = b.json()
    assert bd["booking_id"].startswith("AURA-FLT-")
    assert bd["status"] == "confirmed"
    assert bd["verified"] is True
    # Fetch
    g = session.get(f"{API}/booking/{bd['booking_id']}")
    assert g.status_code == 200
    assert g.json()["option"]["id"] == oid


def test_book_generated_hotel(session):
    s = session.post(f"{API}/search", json={"intent": "hotel", "params": {"city": "Kolkata"}})
    gen = next((r for r in s.json()["results"] if r["id"].startswith("GHT-")), None)
    assert gen is not None
    b = session.post(f"{API}/book", json={
        "intent": "hotel", "option_id": gen["id"], "quantity": 1, "nights": 2,
        "confirmed": True, "user_request": "TEST_gen_hotel",
    })
    assert b.status_code == 200
    assert b.json()["booking_id"].startswith("AURA-HOT-")


def test_book_generated_movie(session):
    s = session.post(f"{API}/search", json={"intent": "movie", "params": {"city": "Patna"}})
    gen = next((r for r in s.json()["results"] if r["id"].startswith("GMV-")), None)
    assert gen is not None
    b = session.post(f"{API}/book", json={
        "intent": "movie", "option_id": gen["id"], "quantity": 2,
        "confirmed": True, "user_request": "TEST_gen_movie",
    })
    assert b.status_code == 200
    assert b.json()["booking_id"].startswith("AURA-MOV-")


# ---------- Deterministic generator ----------
def test_generator_is_deterministic(session):
    body = {"intent": "flight", "params": {"source": "Kolkata", "destination": "Delhi"}}
    r1 = session.post(f"{API}/search", json=body).json()["results"]
    r2 = session.post(f"{API}/search", json=body).json()["results"]
    ids1 = [r["id"] for r in r1]
    ids2 = [r["id"] for r in r2]
    assert ids1 == ids2
    prices1 = [r["price"] for r in r1]
    prices2 = [r["price"] for r in r2]
    assert prices1 == prices2


# ---------- /api/meta expanded cities ----------
def test_meta_supported_cities(session):
    r = session.get(f"{API}/meta")
    assert r.status_code == 200
    cities = r.json()["supported_cities"]
    for c in ["Kolkata", "Chennai", "Pune", "Goa", "Visakhapatnam", "Thiruvananthapuram", "Mumbai", "Bengaluru"]:
        assert c in cities, f"{c} missing from supported_cities"
    assert len(cities) >= 20
