"""Configurable simulated booking charges and GST rates. These are not real rates."""

GST_RATES = {
    "flight_percent": 5,
    "train_ac_percent": 5,
    "train_non_ac_percent": 0,
    "bus_percent": 5,
    "hotel_slabs": ((1000, 0), (7500, 5), (float("inf"), 18)),
    "event_percent": 18,
}

SIMULATED_CHARGES = {
    "flight_fuel_percent": 7,
    "flight_airport_fee_per_passenger": 350,
    "flight_convenience_per_passenger": 149,
    "train_reservation_per_passenger": 40,
    "train_superfast_per_passenger": 30,
    "train_catering_by_class": {"Sleeper": 0, "SL": 0, "AC Chair Car": 80, "3A": 120, "2A": 160, "1A": 200},
    "train_convenience_per_passenger": 20,
    "bus_platform_per_passenger": 49,
    "hotel_service_percent": 5,
    "event_convenience_per_ticket": 35,
    "travel_insurance_per_passenger": 99,
    "promotions": {
        "AURA100": {"type": "fixed", "value": 100},
        "WELCOME10": {"type": "percent", "value": 10, "maximum": 500},
    },
}
