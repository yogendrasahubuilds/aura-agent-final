"""Validate and print the standalone simulated destination dataset."""
import json
import re
import sys
from pathlib import Path

from destination_data import DESTINATIONS, generateDestinationHotels, isInSeason


ROOT = Path(__file__).parent
with (ROOT / "config" / "cities.json").open(encoding="utf-8") as city_file:
    allowed_cities = {
        city["name"].casefold()
        for city in json.load(city_file)["cities"]
    }

BRANDS = re.compile(
    r"\b(taj|oberoi|marriott|hyatt|fern|itc|radisson|hilton|sheraton|"
    r"leela|accor|novotel|ibis|westin|holiday inn|trident)\b",
    re.IGNORECASE,
)
errors = []
hotel_ids = set()
table_rows = []

for destination in DESTINATIONS:
    for gateway_type in ("airportCity", "railCity"):
        gateway_city = destination.get("gateway", {}).get(gateway_type)
        if not gateway_city or gateway_city.casefold() not in allowed_cities:
            errors.append(
                f"{destination['name']}: {gateway_type} is not in the configured city list: "
                f"{gateway_city!r}"
            )
    if len(destination.get("attractions", [])) < 6:
        errors.append(f"{destination['name']}: fewer than 6 attractions")

    for transfer in destination.get("transfers", []):
        distance = transfer.get("distanceKm")
        price = transfer.get("priceINR")
        if not isinstance(distance, (int, float)) or distance <= 0:
            errors.append(f"{destination['name']}: transfer has missing/invalid distance")
        if (
            not isinstance(price, list)
            or len(price) != 2
            or any(not isinstance(amount, (int, float)) or amount < 0 for amount in price)
        ):
            errors.append(f"{destination['name']}: transfer has missing/invalid price")
        if transfer.get("bookable") is not False:
            errors.append(f"{destination['name']}: transfer must be estimate-only")

    hotels = generateDestinationHotels(destination["id"])
    if not hotels:
        errors.append(f"{destination['name']}: no generated hotels")
    if not 6 <= len(hotels) <= 8:
        errors.append(f"{destination['name']}: generated hotel count is outside 6-8")
    categories = {hotel["category"] for hotel in hotels}
    expected_categories = {"Hostel/Budget", "2-star", "3-star", "4-star", "5-star"}
    if categories != expected_categories:
        errors.append(f"{destination['name']}: generated hotels do not cover all categories")
    for hotel in hotels:
        if hotel["id"] in hotel_ids:
            errors.append(f"Duplicate hotel ID: {hotel['id']}")
        hotel_ids.add(hotel["id"])
        if BRANDS.search(hotel["hotel"]):
            errors.append(f"{destination['name']}: real hotel brand in name {hotel['hotel']!r}")

    prices = [hotel["price_per_night"] for hotel in hotels]
    best_season = destination["season"]["bestLabel"]
    table_rows.append(
        (
            destination["id"],
            destination["state"],
            ", ".join(destination["themes"]),
            destination["gateway"]["airportCity"],
            destination["gateway"]["railCity"],
            len(destination["transfers"]),
            len(hotels),
            min(prices) if prices else "-",
            max(prices) if prices else "-",
            best_season,
        )
    )

if errors:
    print("DESTINATION VERIFICATION FAILED:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print(
    f"{'ID':<9} {'State':<17} {'Themes':<37} {'Air gateway':<16} "
    f"{'Rail gateway':<16} {'Xfers':>5} {'Hotels':>6} {'Min Rs':>9} "
    f"{'Max Rs':>9}  Best season"
)
for row in table_rows:
    destination_id, state, themes, air, rail, transfer_count, count, minimum, maximum, season = row
    print(
        f"{destination_id:<9} {state:<17} {themes[:37]:<37} {air:<16} "
        f"{rail:<16} {transfer_count:>5} {count:>6} {minimum:>9} {maximum:>9}  {season}"
    )

samples = (
    ("Manali", "July"),
    ("Leh-Ladakh", "January"),
    ("Goa", "May"),
    ("Munnar", "October"),
    ("Jagdalpur-Chitrakote", "August"),
)
print("\nSample season lookups:")
for name, month in samples:
    print(f"{name} in {month}: {'in season' if isInSeason(name, month) else 'not in season'}")
print(f"\nVerified {len(DESTINATIONS)} destinations and {len(hotel_ids)} unique generated hotels.")
