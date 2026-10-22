"""Verify simulated hotel inventory and per-day local transport by configured city."""
from generator import METRO_CITIES, TRANSPORT_CITIES, generate_local_transport
from tools import hotel_search

SAMPLE_CITIES = [
    "Delhi",
    "Mumbai",
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Kolkata",
    "Pune",
    "Goa",
    "Raipur",
    "Bhilai",
]
BASE_PRICE_BANDS = {
    "Hostel/Budget": (600, 1200),
    "2-star": (1200, 2500),
    "3-star": (2500, 4500),
    "4-star": (4500, 8000),
    "5-star": (8000, 20000),
}


def main() -> None:
    seen_hotel_ids: set[str] = set()
    city_results: dict[str, list[dict]] = {}
    for city in TRANSPORT_CITIES:
        hotels = hotel_search(city)
        if not 8 <= len(hotels) <= 10:
            raise AssertionError(f"{city} returned {len(hotels)} hotels, expected 8-10")
        ids = [hotel["id"] for hotel in hotels]
        if len(ids) != len(set(ids)):
            raise AssertionError(f"Duplicate hotel IDs in {city}")
        duplicates = seen_hotel_ids.intersection(ids)
        if duplicates:
            raise AssertionError(f"Hotel IDs collide between cities: {sorted(duplicates)}")
        seen_hotel_ids.update(ids)
        if hotel_search(city) != hotels:
            raise AssertionError(f"Hotel results changed across identical searches for {city}")

        generated_categories = {
            hotel.get("category")
            for hotel in hotels
            if hotel.get("generated")
        }
        expected_categories = {"Hostel/Budget", "2-star", "3-star", "4-star", "5-star"}
        if generated_categories != expected_categories:
            raise AssertionError(f"{city} does not have generated hotels across all categories")
        multiplier = TRANSPORT_CITIES[city]["hotelPriceMultiplier"]
        for hotel in hotels:
            if not hotel.get("generated"):
                continue
            low, high = BASE_PRICE_BANDS[hotel["category"]]
            if not low * multiplier <= hotel["price_per_night"] <= high * multiplier:
                raise AssertionError(f"{city} {hotel['category']} rate is outside its configured price band")
            if not hotel.get("location") or not hotel.get("room_type") or not hotel.get("amenities") or not hotel.get("rating"):
                raise AssertionError(f"Incomplete hotel details for {hotel['id']}")
        city_results[city] = hotels

        local_options = generate_local_transport(city)
        local_ids = [option["id"] for option in local_options]
        if len(local_ids) != len(set(local_ids)):
            raise AssertionError(f"Duplicate local transport IDs in {city}")
        modes = {option["mode"] for option in local_options}
        required_modes = {"Auto rickshaw", "Taxi", "Local bus"}
        if not required_modes.issubset(modes):
            raise AssertionError(f"{city} is missing local transport modes: {required_modes - modes}")
        if ("Metro" in modes) != (city in METRO_CITIES):
            raise AssertionError(f"Metro availability mismatch for {city}")
        if any(option["price_per_day"] <= 0 for option in local_options):
            raise AssertionError(f"Invalid local transport daily estimate in {city}")
        if generate_local_transport(city) != local_options:
            raise AssertionError(f"Local transport estimates changed across identical searches for {city}")

    print("Hotel inventory by sample city (simulated INR per night):")
    for city in SAMPLE_CITIES:
        hotels = city_results[city]
        prices = [hotel["price_per_night"] for hotel in hotels]
        print(f"  {city}: {len(hotels)} hotels; Rs {min(prices):,}..Rs {max(prices):,}")

    print("\nLocal transport estimates by sample city (simulated INR per day):")
    for city in SAMPLE_CITIES:
        options = generate_local_transport(city)
        estimates = ", ".join(
            f"{option['mode']} Rs {option['price_per_day']:,}"
            for option in options
        )
        print(f"  {city}: {estimates}")


if __name__ == "__main__":
    main()
