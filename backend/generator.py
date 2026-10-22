"""Dynamic mock-option generator for AURA.
Produces realistic, deterministic (seeded) options for ANY Indian city / route
so searches aren't limited to the hand-curated dataset. All options are still SIMULATED/DEMO.
Generated options are cached in-memory keyed by their generated ID so booking can resolve them.
"""
import random
import hashlib
import json
import math
from datetime import date as date_type, datetime, timedelta
from pathlib import Path
from typing import Optional, List

# City database (title-case canonical name + airport metadata for flights)
CITIES = {
    "Bhilai": {"airport": None, "aliases": ["bhilai"]},
    "Raipur": {"airport": ("RPR", "Swami Vivekananda Airport, Raipur"), "aliases": ["raipur"]},
    "Delhi": {"airport": ("DEL", "Indira Gandhi International Airport, Delhi"), "aliases": ["delhi", "new delhi"]},
    "Mumbai": {"airport": ("BOM", "Chhatrapati Shivaji International Airport, Mumbai"), "aliases": ["mumbai", "bombay"]},
    "Bengaluru": {"airport": ("BLR", "Kempegowda International Airport, Bengaluru"), "aliases": ["bengaluru", "bangalore"]},
    "Kolkata": {"airport": ("CCU", "Netaji Subhash Chandra Bose Intl Airport, Kolkata"), "aliases": ["kolkata", "calcutta"]},
    "Chennai": {"airport": ("MAA", "Chennai International Airport"), "aliases": ["chennai", "madras"]},
    "Hyderabad": {"airport": ("HYD", "Rajiv Gandhi International Airport, Hyderabad"), "aliases": ["hyderabad"]},
    "Pune": {"airport": ("PNQ", "Pune International Airport"), "aliases": ["pune"]},
    "Ahmedabad": {"airport": ("AMD", "Sardar Vallabhbhai Patel Intl Airport, Ahmedabad"), "aliases": ["ahmedabad"]},
    "Jaipur": {"airport": ("JAI", "Jaipur International Airport"), "aliases": ["jaipur"]},
    "Lucknow": {"airport": ("LKO", "Chaudhary Charan Singh Intl Airport, Lucknow"), "aliases": ["lucknow"]},
    "Goa": {"airport": ("GOI", "Dabolim Airport, Goa"), "aliases": ["goa", "panjim", "panaji"]},
    "Chandigarh": {"airport": ("IXC", "Chandigarh International Airport"), "aliases": ["chandigarh"]},
    "Nagpur": {"airport": ("NAG", "Dr. Babasaheb Ambedkar Intl Airport, Nagpur"), "aliases": ["nagpur"]},
    "Indore": {"airport": ("IDR", "Devi Ahilya Bai Holkar Airport, Indore"), "aliases": ["indore"]},
    "Bhopal": {"airport": ("BHO", "Raja Bhoj Airport, Bhopal"), "aliases": ["bhopal"]},
    "Visakhapatnam": {"airport": ("VTZ", "Visakhapatnam International Airport"), "aliases": ["visakhapatnam", "vizag"]},
    "Kochi": {"airport": ("COK", "Cochin International Airport"), "aliases": ["kochi", "cochin"]},
    "Coimbatore": {"airport": ("CJB", "Coimbatore International Airport"), "aliases": ["coimbatore"]},
    "Guwahati": {"airport": ("GAU", "Lokpriya Gopinath Bordoloi Intl Airport, Guwahati"), "aliases": ["guwahati"]},
    "Patna": {"airport": ("PAT", "Jay Prakash Narayan Airport, Patna"), "aliases": ["patna"]},
    "Thiruvananthapuram": {"airport": ("TRV", "Trivandrum International Airport"), "aliases": ["thiruvananthapuram", "trivandrum"]},
    "Varanasi": {"airport": ("VNS", "Lal Bahadur Shastri Airport, Varanasi"), "aliases": ["varanasi", "banaras"]},
    "Amritsar": {"airport": ("ATQ", "Sri Guru Ram Dass Jee Intl Airport, Amritsar"), "aliases": ["amritsar"]},
    "Surat": {"airport": ("STV", "Surat Airport"), "aliases": ["surat"]},
    "Udaipur": {"airport": ("UDR", "Maharana Pratap Airport, Udaipur"), "aliases": ["udaipur"]},
    "Dehradun": {"airport": ("DED", "Jolly Grant Airport, Dehradun"), "aliases": ["dehradun"]},
    "Ranchi": {"airport": ("IXR", "Birsa Munda Airport, Ranchi"), "aliases": ["ranchi"]},
    "Bhubaneswar": {"airport": ("BBI", "Biju Patnaik International Airport, Bhubaneswar"), "aliases": ["bhubaneswar"]},
    "Agra": {"airport": None, "aliases": ["agra"]},
    "Shimla": {"airport": None, "aliases": ["shimla"]},
    "Rishikesh": {"airport": None, "aliases": ["rishikesh"]},
}

CITY_ALIAS_TO_CANONICAL = {alias: name for name, meta in CITIES.items() for alias in meta["aliases"]}

with (Path(__file__).parent / "config" / "cities.json").open(encoding="utf-8") as _city_file:
    _CITY_CONFIG = json.load(_city_file)

TRANSPORT_CITIES = {city["name"]: city for city in _CITY_CONFIG["cities"]}
for _city in _CITY_CONFIG["cities"]:
    CITY_ALIAS_TO_CANONICAL.setdefault(_city["name"].lower(), _city["name"])


def resolve_city(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return CITY_ALIAS_TO_CANONICAL.get(name.strip().lower(), name.strip().title() if name else None)


def haversine_km(source: str, destination: str) -> Optional[int]:
    """Return approximate great-circle distance between configured city centers."""
    source_city = TRANSPORT_CITIES.get(resolve_city(source) or "")
    destination_city = TRANSPORT_CITIES.get(resolve_city(destination) or "")
    if not source_city or not destination_city:
        return None
    lat1, lon1 = math.radians(source_city["latitude"]), math.radians(source_city["longitude"])
    lat2, lon2 = math.radians(destination_city["latitude"]), math.radians(destination_city["longitude"])
    lat_delta = lat2 - lat1
    lon_delta = lon2 - lon1
    value = math.sin(lat_delta / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(lon_delta / 2) ** 2
    return int(round(6371 * 2 * math.asin(math.sqrt(value))))


def _transport_rng(mode: str, source: str, destination: str, travel_date: Optional[str]) -> random.Random:
    return _rng(mode, resolve_city(source), resolve_city(destination), travel_date or "undated")


def _travel_times(rng: random.Random, duration_minutes: int, travel_date: Optional[str]) -> tuple[str, str, str]:
    departure = _random_time(rng)
    try:
        base_date = date_type.fromisoformat(travel_date) if travel_date else date_type(2000, 1, 1)
    except ValueError:
        base_date = date_type(2000, 1, 1)
    depart_dt = datetime.combine(base_date, datetime.strptime(departure, "%H:%M").time())
    arrival_dt = depart_dt + timedelta(minutes=duration_minutes)
    return departure, arrival_dt.strftime("%H:%M"), arrival_dt.date().isoformat()


def _peak_price_factor(travel_date: Optional[str]) -> float:
    if not travel_date:
        return 1.0
    try:
        month = date_type.fromisoformat(travel_date).month
    except ValueError:
        return 1.0
    return 1.22 if month in {10, 11, 12, 1, 2, 5, 6} else 0.78


def _cache_transport_options(intent: str, options: List[dict]) -> List[dict]:
    for option in options:
        _GENERATED_CACHE[option["id"]] = {"intent": intent, "data": option}
    return options


def _route_generated_id(prefix: str, mode: str, source: str, destination: str, travel_date: Optional[str], index: int) -> str:
    return f"{prefix}-{_seed(mode, source, destination, travel_date or 'undated', index):012X}"


def generate_trains(source: str, destination: str, count: int = 6, travel_date: Optional[str] = None) -> List[dict]:
    source = resolve_city(source) or source
    destination = resolve_city(destination) or destination
    src_city = TRANSPORT_CITIES.get(source)
    dst_city = TRANSPORT_CITIES.get(destination)
    distance = haversine_km(source, destination)
    if source == destination or not src_city or not dst_city or not src_city["railStations"] or not dst_city["railStations"]:
        return []

    rng = _transport_rng("trains", source, destination, travel_date)
    duration_minutes = max(35, int(distance * 60 / rng.randint(55, 78)) + rng.randint(20, 80))
    classes = ["SL", "3A", "2A", "1A", "SL", "3A", "2A", "1A"]
    multipliers = [0.72, 1.0, 1.45, 2.35, 0.85, 1.2, 1.7, 2.9]
    base_fare = max(250, int(distance * 0.78 + 100))
    options = []
    for index in range(min(max(count, 6), 8)):
        departure, arrival, arrival_date = _travel_times(rng, duration_minutes, travel_date)
        class_name = classes[index]
        fare = int(round(base_fare * multipliers[index] / 10) * 10)
        option_id = _route_generated_id("TRN", "train", source, destination, travel_date, index)
        options.append({
            "id": option_id,
            "train_name": f"AURA Simulated {['Intercity', 'Express', 'Superfast', 'Premium', 'Passenger', 'Mail', 'Superfast', 'Premium'][index]}",
            "train_no": f"SIM-{_seed(source, destination, travel_date or 'undated', index) % 100000:05d}",
            "source": source,
            "destination": destination,
            "departure": departure,
            "arrival": arrival,
            "duration": f"{duration_minutes // 60}h {duration_minutes % 60:02d}m",
            "price": fare,
            "seats_available": rng.randint(8, 72),
            "class": class_name,
            "date": travel_date,
            "arrival_date": arrival_date,
            "distance_km": distance,
            "generated": True,
        })
    return _cache_transport_options("train", options)


def generate_buses(source: str, destination: str, count: int = 6, travel_date: Optional[str] = None) -> List[dict]:
    source = resolve_city(source) or source
    destination = resolve_city(destination) or destination
    src_city = TRANSPORT_CITIES.get(source)
    dst_city = TRANSPORT_CITIES.get(destination)
    distance = haversine_km(source, destination)
    if source == destination or not src_city or not dst_city or not src_city["busHub"] or not dst_city["busHub"] or distance is None or distance > 1000:
        return []

    rng = _transport_rng("buses", source, destination, travel_date)
    duration_minutes = max(45, int(distance * 60 / rng.randint(52, 72)) + rng.randint(15, 60))
    classes = ["Non-AC Seater", "AC Seater", "AC Sleeper", "Volvo", "AC Sleeper", "Volvo", "AC Seater", "Volvo"]
    multipliers = [0.62, 0.95, 1.35, 1.85, 1.65, 2.4, 1.1, 3.1]
    base_fare = max(250, int(distance * 1.15 + 120))
    operators = ["IntrCity SmartBus", "Zingbus", "VRL Travels", "SRS Travels", "Orange Travels", "Neeta Travels", "KSRTC Airavat", "AURA Premium Coach"]
    options = []
    for index in range(min(max(count, 6), 8)):
        departure, arrival, arrival_date = _travel_times(rng, duration_minutes, travel_date)
        fare = int(round(base_fare * multipliers[index] / 10) * 10)
        option_id = _route_generated_id("BUS", "bus", source, destination, travel_date, index)
        options.append({
            "id": option_id,
            "operator": operators[index],
            "bus_no": f"SIM-BUS-{_seed(source, destination, travel_date or 'undated', index) % 100000:05d}",
            "source": source,
            "destination": destination,
            "departure": departure,
            "arrival": arrival,
            "duration": f"{duration_minutes // 60}h {duration_minutes % 60:02d}m",
            "price": fare,
            "seats_available": rng.randint(6, 42),
            "class": classes[index],
            "date": travel_date,
            "arrival_date": arrival_date,
            "distance_km": distance,
            "generated": True,
        })
    return _cache_transport_options("bus", options)


# ---------- Movies ----------
MOVIE_CATALOG = [
    "Mirzapur: The Film", "Stree 2", "Pushpa 2: The Rule", "Kalki 2898 AD",
    "Jawan Returns", "Devara Part 2", "Singham Again", "Fighter 2",
    "Bhool Bhulaiyaa 3", "Dunki 2", "Animal Park", "Chhaava",
]
CINEMA_CHAINS = ["PVR", "INOX", "Cinepolis", "Miraj Cinemas", "Carnival Cinemas"]
MALLS = ["City Mall", "Phoenix", "Treasure Island", "Magneto Mall", "DB City", "Infinity Mall", "Elante Mall", "Forum Mall", "Nexus Mall", "Oberoi Mall"]
LOCALITIES = ["Civil Lines", "MG Road", "Sector 17", "Nehru Place", "Pandri", "Rajouri", "Koregaon Park", "Banjara Hills", "Koramangala", "Salt Lake"]
SCREEN_FORMATS = [("Audi 1", "2D"), ("Audi 2", "2D"), ("IMAX", "IMAX 2D"), ("Audi 3", "2D"), ("Director's Cut", "Dolby Atmos"), ("4DX", "4DX"), ("Gold", "Recliner 2D")]
SHOW_TIMES = ["10:00", "12:30", "14:15", "15:45", "17:30", "18:45", "19:30", "20:15", "21:00", "22:30"]


# ---------- Hotels ----------
HOTEL_LOCALITY_TEMPLATES = {
    "Hostel/Budget": ["{locality} Hostel", "{locality} Budget Stay"],
    "2-star": ["{locality} Standard Inn", "{locality} City Rooms"],
    "3-star": ["{locality} Deluxe Stay", "{locality} Comfort Lodge"],
    "4-star": ["{locality} Superior Residence", "{locality} Club Stay"],
    "5-star": ["{locality} Signature Suites", "{locality} Grand Suites"],
}
AMENITIES_POOL = ["Free WiFi", "Breakfast included", "Swimming Pool", "Spa", "Gym", "Airport Transfer", "Pet Friendly", "24h Room Service", "Parking", "Restaurant", "Business Center", "Butler"]


# ---------- Flights ----------
AIRLINES = [
    ("IndiGo", "6E"), ("Air India", "AI"), ("Vistara", "UK"),
    ("Akasa Air", "QP"), ("SpiceJet", "SG"), ("Air India Express", "IX"),
]
TRAVEL_CLASSES = [("Economy", 1.0), ("Premium Economy", 1.5), ("Business", 2.8)]


# ---------- Generator cache ----------
# Keyed by generated option_id, so /api/book can resolve it later.
_GENERATED_CACHE: dict = {}


def _seed(*parts) -> int:
    s = "|".join(str(p) for p in parts if p is not None)
    h = hashlib.md5(s.encode()).hexdigest()
    return int(h[:12], 16)


def _rng(*parts) -> random.Random:
    return random.Random(_seed(*parts))


def _city_price_tier(city: str) -> float:
    """Tier multiplier — metros slightly more expensive."""
    metros = {"Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Pune"}
    tier2 = {"Ahmedabad", "Jaipur", "Lucknow", "Goa", "Chandigarh", "Kochi", "Visakhapatnam", "Thiruvananthapuram"}
    if city in metros:
        return 1.25
    if city in tier2:
        return 1.08
    return 0.9


def _route_distance_proxy(src: str, dst: str) -> int:
    """Rough proxy for route distance using seeded random (100-2500 km)."""
    r = _rng("dist", *sorted([src, dst]))
    return r.randint(600, 2400)


def _duration_from_distance(km: int) -> str:
    minutes = int(km / 10) + 25
    h, m = divmod(minutes, 60)
    return f"{h}h {m:02d}m"


def generate_movies(city: str, movie_hint: Optional[str] = None, count: int = 6) -> List[dict]:
    city = resolve_city(city) or city
    rng = _rng("movies", city, movie_hint)
    results = []
    chosen_movies = []
    if movie_hint:
        # Pick movies whose name contains the hint, else fall back
        matches = [m for m in MOVIE_CATALOG if movie_hint.lower() in m.lower()]
        chosen_movies = matches if matches else [movie_hint.title()]
        # Also show the hint as a movie if it doesn't appear exactly
        if movie_hint.title() not in chosen_movies:
            chosen_movies.insert(0, movie_hint.title())
    else:
        chosen_movies = rng.sample(MOVIE_CATALOG, k=min(4, len(MOVIE_CATALOG)))

    tier = _city_price_tier(city)
    for i in range(count):
        movie = chosen_movies[i % len(chosen_movies)]
        chain = rng.choice(CINEMA_CHAINS)
        mall = rng.choice(MALLS)
        locality = rng.choice(LOCALITIES)
        screen, fmt = rng.choice(SCREEN_FORMATS)
        time = rng.choice(SHOW_TIMES)
        base_price = rng.randint(140, 260)
        if fmt == "IMAX 2D":
            base_price = int(base_price * 1.4)
        elif fmt == "Dolby Atmos":
            base_price = int(base_price * 1.6)
        elif fmt == "4DX":
            base_price = int(base_price * 1.9)
        elif fmt == "Recliner 2D":
            base_price = int(base_price * 1.5)
        price = int(round(base_price * tier / 10) * 10)
        provider = f"BookMyShow via {chain}"
        option_id = f"GMV-{_seed(city, movie, chain, mall, i):x}"[:16].upper()
        opt = {
            "id": option_id,
            "movie": movie,
            "cinema": f"{chain} {mall}",
            "city": city,
            "location": f"{locality}, {city}",
            "time": time,
            "price": price,
            "seats_available": rng.randint(14, 85),
            "screen": screen,
            "format": fmt,
            "provider": provider,
            "generated": True,
        }
        _GENERATED_CACHE[option_id] = {"intent": "movie", "data": opt}
        results.append(opt)
    return results


def generate_hotels(city: str, count: int = 6) -> List[dict]:
    city = resolve_city(city) or city
    rng = _rng("hotels", city)
    city_config = TRANSPORT_CITIES.get(city)
    hotel_multiplier = city_config["hotelPriceMultiplier"] if city_config else 1.0
    categories = [
        ("Hostel/Budget", 600, 1200, ["Dorm Bed", "Basic Room"]),
        ("2-star", 1200, 2500, ["Standard Room", "Standard Twin Room"]),
        ("3-star", 2500, 4500, ["Deluxe Room", "Deluxe Twin Room"]),
        ("4-star", 4500, 8000, ["Superior Room", "Club Room"]),
        ("5-star", 8000, 20000, ["Suite", "Luxury Suite"]),
    ]
    category_choices = [
        (category, low, high, room_types, index)
        for index, (category, low, high, room_types) in enumerate(categories)
    ]
    choices = [
        (category, low, high, room_types, category_index, variant)
        for category, low, high, room_types, category_index in category_choices
        for variant in range(2)
    ]
    category_first = [choice for choice in choices if choice[-1] == 0]
    category_second = [choice for choice in choices if choice[-1] == 1]
    balanced_choices = category_first + category_second
    results = []
    for i, (category, low, high, room_types, category_index, variant) in enumerate(balanced_choices[:max(0, min(count, len(balanced_choices)))]):
        locality = rng.choice(LOCALITIES)
        room_type = room_types[variant]
        price = int(round(rng.randint(low, high) * hotel_multiplier))
        rating = round(rng.uniform(3.6, 4.9), 1)
        amenities = rng.sample(AMENITIES_POOL, k=rng.randint(3, 6))
        aggregator = rng.choice(["Booking.com", "MakeMyTrip", "Goibibo", "Agoda", "Hotels.com"])
        option_id = f"GHT-{_seed('hotels', city, category, variant):012X}"
        opt = {
            "id": option_id,
            "hotel": HOTEL_LOCALITY_TEMPLATES[category][variant].format(locality=locality),
            "city": city,
            "location": f"{locality}, {city}",
            "room_type": room_type,
            "price_per_night": price,
            "rooms_available": rng.randint(2, 18),
            "rating": rating,
            "amenities": amenities,
            "provider": aggregator,
            "category": category,
            "star_rating": int(category[0]) if category[0].isdigit() else 0,
            "simulated": True,
            "generated": True,
        }
        _GENERATED_CACHE[option_id] = {"intent": "hotel", "data": opt}
        results.append(opt)
    return results


METRO_CITIES = {
    "Agra", "Ahmedabad", "Bengaluru", "Bhopal", "Chennai", "Delhi",
    "Hyderabad", "Indore", "Jaipur", "Kochi", "Kolkata", "Lucknow",
    "Mumbai", "Nagpur", "Pune",
}

LOCAL_TRANSPORT_BASES = {
    "metro": {
        "Auto rickshaw": (650, 850),
        "Taxi": (1900, 2700),
        "Metro": (250, 500),
        "Local bus": (80, 180),
    },
    "tier1": {
        "Auto rickshaw": (450, 700),
        "Taxi": (1400, 2200),
        "Metro": (220, 420),
        "Local bus": (70, 150),
    },
    "tier2": {
        "Auto rickshaw": (300, 550),
        "Taxi": (900, 1700),
        "Metro": (180, 350),
        "Local bus": (50, 120),
    },
}


def generate_local_transport(city: str) -> List[dict]:
    """Create stable simulated per-day local mobility estimates from the city profile."""
    city = resolve_city(city) or city
    city_config = TRANSPORT_CITIES.get(city)
    tier = city_config["cityTier"] if city_config else "tier2"
    rng = _rng("local-transport", city)
    estimates = []
    for mode, (low, high) in LOCAL_TRANSPORT_BASES[tier].items():
        if mode == "Metro" and city not in METRO_CITIES:
            continue
        option_id = f"LOC-{_seed('local-transport', city, mode):012X}"
        estimates.append({
            "id": option_id,
            "mode": mode,
            "city": city,
            "price_per_day": rng.randint(low, high),
            "transport_type": mode.lower().replace(" ", "_"),
            "simulated": True,
            "generated": True,
        })
        _GENERATED_CACHE[option_id] = {"intent": "local_transport", "data": estimates[-1]}
    return estimates


def _random_time(rng) -> str:
    h = rng.randint(5, 22)
    m = rng.choice([0, 15, 30, 45])
    return f"{h:02d}:{m:02d}"


def _add_minutes(hhmm: str, mins: int) -> str:
    h, m = map(int, hhmm.split(":"))
    total = h * 60 + m + mins
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def generate_flights(source: str, destination: str, count: int = 6, travel_date: Optional[str] = None) -> List[dict]:
    source = resolve_city(source) or source
    destination = resolve_city(destination) or destination
    src_city = TRANSPORT_CITIES.get(source)
    dst_city = TRANSPORT_CITIES.get(destination)
    distance = haversine_km(source, destination)
    if (
        source == destination
        or not src_city
        or not dst_city
        or not src_city["airport"]
        or not dst_city["airport"]
        or distance is None
        or distance <= 300
    ):
        return []

    rng = _transport_rng("flights", source, destination, travel_date)
    src_meta = src_city["airport"]
    dst_meta = dst_city["airport"]
    src_code, src_name = src_meta["iata"], src_meta["name"]
    dst_code, dst_name = dst_meta["iata"], dst_meta["name"]
    dur_mins = max(40, int(distance / 690 * 60) + 35)
    duration = f"{dur_mins // 60}h {dur_mins % 60:02d}m"
    base_fare = max(1800, int(950 + distance * 2.15))
    peak_factor = _peak_price_factor(travel_date)
    classes = ["Economy", "Economy", "Economy", "Premium Economy", "Premium Economy", "Business", "Economy", "Business"]
    fare_multipliers = [0.72, 0.9, 1.08, 1.45, 1.8, 2.65, 1.15, 3.15]

    results = []
    for i in range(min(max(count, 6), 8)):
        airline, prefix = AIRLINES[i % len(AIRLINES)]
        flight_num = f"{prefix}-{_seed(source, destination, travel_date or 'undated', i) % 9000 + 1000:04d}"
        dep, arr, arrival_date = _travel_times(rng, dur_mins, travel_date)
        cls = classes[i]
        price = int(round(base_fare * peak_factor * fare_multipliers[i] / 50) * 50)
        aggregator = f"{airline} Direct"
        option_id = _route_generated_id("GFL", "flight", source, destination, travel_date, i)
        opt = {
            "id": option_id,
            "airline": airline,
            "flight_no": flight_num,
            "source": source,
            "destination": destination,
            "source_airport": f"{src_name} ({src_code})",
            "destination_airport": f"{dst_name} ({dst_code})",
            "departure": dep,
            "arrival": arr,
            "duration": duration,
            "price": price,
            "seats_available": rng.randint(4, 48),
            "class": cls,
            "provider": aggregator,
            "date": travel_date,
            "arrival_date": arrival_date,
            "distance_km": distance,
            "generated": True,
        }
        results.append(opt)
    return _cache_transport_options("flight", results)


def get_cached_generated(option_id: str) -> Optional[dict]:
    entry = _GENERATED_CACHE.get(option_id)
    return entry["data"] if entry else None


def annotate_with_comparison(results: List[dict], price_key: str) -> List[dict]:
    """Add 'cheapest', 'save_pct_vs_max', 'premium_pct_vs_min' flags for easy UI comparison."""
    if not results:
        return results
    prices = [r[price_key] for r in results if r.get(price_key) is not None]
    if not prices:
        return results
    min_p = min(prices)
    max_p = max(prices)
    for r in results:
        p = r.get(price_key)
        if p is None:
            continue
        r["is_cheapest"] = p == min_p
        r["is_premium"] = p == max_p and max_p > min_p
        if max_p > 0:
            r["save_pct_vs_max"] = int(round(100 * (max_p - p) / max_p))
        else:
            r["save_pct_vs_max"] = 0
    # Sort cheapest first for clarity
    results.sort(key=lambda r: r.get(price_key, 10**9))
    return results
