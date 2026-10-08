"""Dynamic mock-option generator for AURA.
Produces realistic, deterministic (seeded) options for ANY Indian city / route
so searches aren't limited to the hand-curated dataset. All options are still SIMULATED/DEMO.
Generated options are cached in-memory keyed by their generated ID so booking can resolve them.
"""
import random
import hashlib
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


def resolve_city(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return CITY_ALIAS_TO_CANONICAL.get(name.strip().lower(), name.strip().title() if name else None)


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
HOTEL_BRANDS = ["Taj", "ITC", "Oberoi", "JW Marriott", "Hyatt", "Radisson", "Sayaji", "Lemon Tree", "The Fern", "Ginger", "OYO Townhouse", "FabHotel", "Treebo", "The Park"]
HOTEL_SUFFIXES = ["Palace", "Grand", "Residency", "Inn", "Boutique", "Signature", "Heritage", "Luxe", "Executive", "Comfort"]
ROOM_TYPES = [("Standard Double", 0.9), ("Deluxe Room", 1.0), ("Premium Room", 1.25), ("Executive Suite", 1.65), ("Luxury King Room", 2.0), ("Royal Club Room", 2.4)]
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
    tier = _city_price_tier(city)
    results = []
    for i in range(count):
        brand = rng.choice(HOTEL_BRANDS)
        suffix = rng.choice(HOTEL_SUFFIXES)
        locality = rng.choice(LOCALITIES)
        room_type, room_mult = rng.choice(ROOM_TYPES)
        base = rng.randint(1800, 7500)
        price = int(round(base * tier * room_mult / 50) * 50)
        rating = round(rng.uniform(3.6, 4.9), 1)
        amenities = rng.sample(AMENITIES_POOL, k=rng.randint(3, 6))
        aggregator = rng.choice(["Booking.com", "MakeMyTrip", "Goibibo", "Agoda", "Hotels.com"])
        option_id = f"GHT-{_seed(city, brand, suffix, locality, i):x}"[:16].upper()
        opt = {
            "id": option_id,
            "hotel": f"{brand} {suffix} {city}",
            "city": city,
            "location": f"{locality}, {city}",
            "room_type": room_type,
            "price_per_night": price,
            "rooms_available": rng.randint(2, 18),
            "rating": rating,
            "amenities": amenities,
            "provider": aggregator,
            "generated": True,
        }
        _GENERATED_CACHE[option_id] = {"intent": "hotel", "data": opt}
        results.append(opt)
    return results


def _random_time(rng) -> str:
    h = rng.randint(5, 22)
    m = rng.choice([0, 15, 30, 45])
    return f"{h:02d}:{m:02d}"


def _add_minutes(hhmm: str, mins: int) -> str:
    h, m = map(int, hhmm.split(":"))
    total = h * 60 + m + mins
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def generate_flights(source: str, destination: str, count: int = 6) -> List[dict]:
    source = resolve_city(source) or source
    destination = resolve_city(destination) or destination
    rng = _rng("flights", source, destination)
    src_meta = CITIES.get(source, {}).get("airport") or (source[:3].upper(), f"{source} Airport")
    dst_meta = CITIES.get(destination, {}).get("airport") or (destination[:3].upper(), f"{destination} Airport")
    src_code, src_name = src_meta
    dst_code, dst_name = dst_meta

    distance = _route_distance_proxy(source, destination)
    duration = _duration_from_distance(distance)
    dur_mins = int(distance / 10) + 25
    base_fare = int(2200 + distance * 1.4)

    results = []
    for i in range(count):
        airline, prefix = rng.choice(AIRLINES)
        flight_num = f"{prefix}-{rng.randint(100, 9999)}"
        dep = _random_time(rng)
        arr = _add_minutes(dep, dur_mins)
        cls, cls_mult = rng.choice(TRAVEL_CLASSES) if i < 2 else ("Economy", 1.0)
        price_variation = rng.uniform(0.78, 1.35)
        price = int(round(base_fare * cls_mult * price_variation / 50) * 50)
        aggregator = rng.choice(["MakeMyTrip", "Cleartrip", "EaseMyTrip", "Yatra", "Goibibo", f"{airline} Direct"])
        option_id = f"GFL-{_seed(source, destination, airline, flight_num, i):x}"[:16].upper()
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
            "generated": True,
        }
        _GENERATED_CACHE[option_id] = {"intent": "flight", "data": opt}
        results.append(opt)
    return results


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
