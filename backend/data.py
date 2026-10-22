"""Mock datasets for AURA — Movies, Hotels, Flights.
All data is SIMULATED / DEMO. Not real inventory."""

MOVIES = [
    # Bhilai
    {"id": "M001", "movie": "Mirzapur: The Film", "cinema": "PVR Surya Treasure Island", "city": "Bhilai", "location": "Nehru Nagar, Bhilai, Chhattisgarh", "time": "19:30", "price": 180, "seats_available": 42, "screen": "Audi 3", "format": "2D"},
    {"id": "M002", "movie": "Mirzapur: The Film", "cinema": "Cinepolis Magneto Mall", "city": "Bhilai", "location": "Labhandi, Bhilai, Chhattisgarh", "time": "20:15", "price": 200, "seats_available": 55, "screen": "Audi 5", "format": "2D"},
    {"id": "M003", "movie": "Mirzapur: The Film", "cinema": "INOX City Centre", "city": "Bhilai", "location": "Smriti Nagar, Bhilai", "time": "22:00", "price": 160, "seats_available": 28, "screen": "Audi 1", "format": "2D"},
    # Raipur
    {"id": "M004", "movie": "Stree 2", "cinema": "City Mall 36 - PVR", "city": "Raipur", "location": "Pandri, Raipur, Chhattisgarh", "time": "18:45", "price": 220, "seats_available": 60, "screen": "Audi 2", "format": "2D"},
    {"id": "M005", "movie": "Pushpa 2: The Rule", "cinema": "INOX Magneto Mall", "city": "Raipur", "location": "Labhandi, Raipur", "time": "21:00", "price": 250, "seats_available": 48, "screen": "IMAX", "format": "IMAX 2D"},
    # Delhi
    {"id": "M006", "movie": "Kalki 2898 AD", "cinema": "PVR Select Citywalk", "city": "Delhi", "location": "Saket, New Delhi", "time": "19:00", "price": 350, "seats_available": 35, "screen": "Gold", "format": "4DX"},
    {"id": "M007", "movie": "Stree 2", "cinema": "Cinepolis DLF Mall of India", "city": "Delhi", "location": "Noida", "time": "20:30", "price": 300, "seats_available": 72, "screen": "Audi 4", "format": "2D"},
    # Mumbai
    {"id": "M008", "movie": "Pushpa 2: The Rule", "cinema": "PVR Phoenix Palladium", "city": "Mumbai", "location": "Lower Parel, Mumbai", "time": "21:30", "price": 400, "seats_available": 20, "screen": "Director's Cut", "format": "Dolby Atmos"},
    {"id": "M009", "movie": "Kalki 2898 AD", "cinema": "INOX R-City", "city": "Mumbai", "location": "Ghatkopar, Mumbai", "time": "18:00", "price": 280, "seats_available": 50, "screen": "Audi 2", "format": "2D"},
    # Bengaluru
    {"id": "M010", "movie": "Mirzapur: The Film", "cinema": "PVR Orion Mall", "city": "Bengaluru", "location": "Rajajinagar, Bengaluru", "time": "19:45", "price": 290, "seats_available": 44, "screen": "Audi 6", "format": "2D"},
]

HOTELS = [
    # Raipur
    {"id": "H001", "hotel": "Jail Road Deluxe Stay", "city": "Raipur", "location": "Jail Road, Raipur, Chhattisgarh", "room_type": "Deluxe Room", "price_per_night": 2500, "rooms_available": 5, "rating": 4.1, "amenities": ["Free WiFi", "Breakfast", "AC"], "category": "3-star", "star_rating": 3},
    {"id": "H002", "hotel": "VIP Road Club Stay", "city": "Raipur", "location": "VIP Road, Raipur", "room_type": "Club Room", "price_per_night": 5800, "rooms_available": 3, "rating": 4.6, "amenities": ["Pool", "Spa", "Breakfast", "Gym"], "category": "4-star", "star_rating": 4},
    {"id": "H003", "hotel": "Civil Lines Deluxe Lodge", "city": "Raipur", "location": "Civil Lines, Raipur", "room_type": "Deluxe Room", "price_per_night": 3400, "rooms_available": 8, "rating": 4.3, "amenities": ["WiFi", "Restaurant", "Parking"], "category": "3-star", "star_rating": 3},
    # Bhilai
    {"id": "H004", "hotel": "Nehru Nagar Standard Inn", "city": "Bhilai", "location": "Nehru Nagar, Bhilai", "room_type": "Standard Room", "price_per_night": 1800, "rooms_available": 10, "rating": 3.9, "amenities": ["WiFi", "AC", "Restaurant"], "category": "2-star", "star_rating": 2},
    {"id": "H005", "hotel": "Supela City Rooms", "city": "Bhilai", "location": "Supela, Bhilai", "room_type": "Standard Room", "price_per_night": 2200, "rooms_available": 4, "rating": 4.0, "amenities": ["WiFi", "Breakfast"], "category": "2-star", "star_rating": 2},
    # Delhi
    {"id": "H006", "hotel": "Diplomatic Enclave Signature Suites", "city": "Delhi", "location": "Diplomatic Enclave, New Delhi", "room_type": "Suite", "price_per_night": 14500, "rooms_available": 6, "rating": 4.8, "amenities": ["Pool", "Spa", "Fine Dining", "Butler"], "category": "5-star", "star_rating": 5},
    {"id": "H007", "hotel": "Barakhamba Grand Suites", "city": "Delhi", "location": "Barakhamba Road, Connaught Place", "room_type": "Suite", "price_per_night": 9200, "rooms_available": 12, "rating": 4.5, "amenities": ["Gym", "Pool", "Breakfast"], "category": "5-star", "star_rating": 5},
    # Mumbai
    {"id": "H008", "hotel": "Juhu Tara Signature Suites", "city": "Mumbai", "location": "Juhu Tara Road, Mumbai", "room_type": "Suite", "price_per_night": 18000, "rooms_available": 4, "rating": 4.7, "amenities": ["Beach view", "Pool", "Spa", "Breakfast"], "category": "5-star", "star_rating": 5},
    {"id": "H009", "hotel": "Goregaon Club Stay", "city": "Mumbai", "location": "Goregaon East, Mumbai", "room_type": "Club Room", "price_per_night": 6400, "rooms_available": 9, "rating": 4.2, "amenities": ["WiFi", "Gym", "Restaurant"], "category": "4-star", "star_rating": 4},
    # Bengaluru
    {"id": "H010", "hotel": "Old Airport Road Grand Suites", "city": "Bengaluru", "location": "Old Airport Road, Bengaluru", "room_type": "Suite", "price_per_night": 15600, "rooms_available": 5, "rating": 4.9, "amenities": ["Pool", "Spa", "Butler", "Fine Dining"], "category": "5-star", "star_rating": 5},
]

FLIGHTS = [
    # Raipur -> Delhi
    {"id": "F001", "airline": "IndiGo", "flight_no": "6E-402", "source": "Raipur", "destination": "Delhi", "source_airport": "Swami Vivekananda Airport, Raipur (RPR)", "destination_airport": "Indira Gandhi International Airport, Delhi (DEL)", "departure": "09:20", "arrival": "11:05", "duration": "1h 45m", "price": 5200, "seats_available": 23, "class": "Economy"},
    {"id": "F002", "airline": "Air India", "flight_no": "AI-461", "source": "Raipur", "destination": "Delhi", "source_airport": "Swami Vivekananda Airport, Raipur (RPR)", "destination_airport": "Indira Gandhi International Airport, Delhi (DEL)", "departure": "14:30", "arrival": "16:20", "duration": "1h 50m", "price": 6100, "seats_available": 18, "class": "Economy"},
    {"id": "F003", "airline": "Vistara", "flight_no": "UK-923", "source": "Raipur", "destination": "Delhi", "source_airport": "Swami Vivekananda Airport, Raipur (RPR)", "destination_airport": "Indira Gandhi International Airport, Delhi (DEL)", "departure": "19:15", "arrival": "21:00", "duration": "1h 45m", "price": 7400, "seats_available": 9, "class": "Economy"},
    # Delhi -> Mumbai
    {"id": "F004", "airline": "IndiGo", "flight_no": "6E-5331", "source": "Delhi", "destination": "Mumbai", "source_airport": "Indira Gandhi International Airport, Delhi (DEL)", "destination_airport": "Chhatrapati Shivaji International Airport, Mumbai (BOM)", "departure": "07:45", "arrival": "10:00", "duration": "2h 15m", "price": 4800, "seats_available": 30, "class": "Economy"},
    {"id": "F005", "airline": "Air India", "flight_no": "AI-801", "source": "Delhi", "destination": "Mumbai", "source_airport": "Indira Gandhi International Airport, Delhi (DEL)", "destination_airport": "Chhatrapati Shivaji International Airport, Mumbai (BOM)", "departure": "12:00", "arrival": "14:10", "duration": "2h 10m", "price": 5500, "seats_available": 22, "class": "Economy"},
    # Mumbai -> Bengaluru
    {"id": "F006", "airline": "Vistara", "flight_no": "UK-863", "source": "Mumbai", "destination": "Bengaluru", "source_airport": "Chhatrapati Shivaji International Airport, Mumbai (BOM)", "destination_airport": "Kempegowda International Airport, Bengaluru (BLR)", "departure": "08:30", "arrival": "10:15", "duration": "1h 45m", "price": 4300, "seats_available": 34, "class": "Economy"},
    {"id": "F007", "airline": "IndiGo", "flight_no": "6E-172", "source": "Mumbai", "destination": "Bengaluru", "source_airport": "Chhatrapati Shivaji International Airport, Mumbai (BOM)", "destination_airport": "Kempegowda International Airport, Bengaluru (BLR)", "departure": "17:45", "arrival": "19:25", "duration": "1h 40m", "price": 3900, "seats_available": 41, "class": "Economy"},
    # Bengaluru -> Delhi
    {"id": "F008", "airline": "IndiGo", "flight_no": "6E-6185", "source": "Bengaluru", "destination": "Delhi", "source_airport": "Kempegowda International Airport, Bengaluru (BLR)", "destination_airport": "Indira Gandhi International Airport, Delhi (DEL)", "departure": "06:00", "arrival": "08:45", "duration": "2h 45m", "price": 5700, "seats_available": 27, "class": "Economy"},
    # Raipur -> Mumbai
    {"id": "F009", "airline": "IndiGo", "flight_no": "6E-734", "source": "Raipur", "destination": "Mumbai", "source_airport": "Swami Vivekananda Airport, Raipur (RPR)", "destination_airport": "Chhatrapati Shivaji International Airport, Mumbai (BOM)", "departure": "11:10", "arrival": "13:25", "duration": "2h 15m", "price": 6200, "seats_available": 15, "class": "Economy"},
    # Delhi -> Bengaluru
    {"id": "F010", "airline": "Air India", "flight_no": "AI-505", "source": "Delhi", "destination": "Bengaluru", "source_airport": "Indira Gandhi International Airport, Delhi (DEL)", "destination_airport": "Kempegowda International Airport, Bengaluru (BLR)", "departure": "15:20", "arrival": "18:10", "duration": "2h 50m", "price": 6800, "seats_available": 11, "class": "Economy"},
]

SUPPORTED_CITIES = sorted({m["city"] for m in MOVIES} | {h["city"] for h in HOTELS} | {f["source"] for f in FLIGHTS} | {f["destination"] for f in FLIGHTS})
