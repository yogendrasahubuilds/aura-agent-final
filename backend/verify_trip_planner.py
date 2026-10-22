"""Verify destination-aware trip plans against the simulated tools and dataset."""
import sys
from datetime import date, datetime

from destination_data import DESTINATIONS, generateDestinationHotels
from trip_planner import build_destination_trip, extract_destination_request


CASES = (
    ("Raipur -> Manali", "Plan a 4 day trip to Manali from Raipur for 2 people under 25000 starting 20 October 2026"),
    ("Bhilai -> Munnar", "Plan a trip to Munnar from Bhilai starting 25 October 2026"),
    ("Raipur -> Goa", "Plan a trip to Goa from Raipur starting 26 October 2026"),
    ("Delhi -> Leh in January", "Plan a trip to Leh from Delhi starting 15 January 2027"),
    ("Mumbai -> Darjeeling", "Plan a trip to Darjeeling from Mumbai starting 20 November 2026"),
    ("Raipur -> Jagdalpur in August", "Plan a trip to Jagdalpur-Chitrakote from Raipur starting 15 August 2027"),
    ("Bhilai -> Agra", "Plan a trip to Agra from Bhilai starting 24 October 2026"),
    ("Pune -> Port Blair", "Plan a trip to Port Blair from Pune starting 30 November 2026"),
    ("Raipur -> Jaipur (culture)", "Plan a culture trip to Jaipur from Raipur starting 30 October 2026"),
    ("Hills in November under 20000 from Raipur", "hills in November under 20000 from Raipur"),
)


def assert_arrivals_not_before_departures(plan, label):
    for leg in plan.get("route_legs", []):
        option = leg.get("option")
        if not option:
            continue
        departure_date = option.get("date") or option.get("travel_date")
        arrival_date = option.get("arrival_date") or departure_date
        if not departure_date or not arrival_date:
            raise AssertionError(f"{label}: transport option lacks date values")
        departure = datetime.fromisoformat(f"{departure_date}T{option['departure']}")
        arrival = datetime.fromisoformat(f"{arrival_date}T{option['arrival']}")
        if arrival < departure:
            raise AssertionError(f"{label}: arrival precedes departure for {option.get('id')}")


def verify_plan(plan, label):
    if plan.get("kind") == "destination_suggestions":
        if not plan.get("suggestions"):
            raise AssertionError(f"{label}: no in-season, in-budget destination suggestions")
        for suggestion in plan["suggestions"]:
            destination = next(
                (item for item in DESTINATIONS if item["id"] == suggestion["id"]),
                None,
            )
            if not destination or not destination["gateway"].get("airportCity") or not destination["gateway"].get("railCity"):
                raise AssertionError(f"{label}: suggestion has no configured gateway")
            if not generateDestinationHotels(destination["name"]):
                raise AssertionError(f"{label}: suggestion has no hotels")
        return
    if plan.get("error"):
        raise AssertionError(f"{label}: {plan['error']}")
    if not plan.get("route_legs"):
        raise AssertionError(f"{label}: missing route leg")
    if plan.get("hotel_count") != 3 or len(plan["options"]["hotel"]) != 3:
        raise AssertionError(f"{label}: expected exactly 3 hotel options")
    destination = plan["destination"]
    if not destination["gateway"].get("airportCity") or not destination["gateway"].get("railCity"):
        raise AssertionError(f"{label}: destination missing a gateway")
    if not generateDestinationHotels(destination["name"]):
        raise AssertionError(f"{label}: destination missing hotel inventory")

    costs = plan["cost_breakdown"]
    parts_total = sum(costs[key] for key in ("transport", "last_mile", "stay", "daily", "taxes_fees"))
    if abs(parts_total - plan["grand_total"]) > 0.01:
        raise AssertionError(
            f"{label}: grand total {plan['grand_total']} does not equal component sum {parts_total}"
        )
    budget_status = plan.get("budget_status")
    if budget_status:
        is_over = plan["grand_total"] > budget_status["budget"]
        if budget_status["over_budget"] != is_over:
            raise AssertionError(f"{label}: over-budget plan marked as fitting (or vice versa)")
        if is_over and budget_status["minimum_needed"] > plan["grand_total"]:
            raise AssertionError(f"{label}: minimum needed exceeds the current plan total")
    assert_arrivals_not_before_departures(plan, label)


def main():
    today = date(2026, 10, 19)
    print(
        f"{'Sample':<42} {'Legs':>4} {'Transport options':>18} {'Hotels':>6} "
        f"{'Days':>5} {'Season':<12} {'Grand total Rs':>16}"
    )
    for label, text in CASES:
        details = extract_destination_request(text, today=today)
        plan = build_destination_trip(details, text)
        verify_plan(plan, label)
        if plan.get("kind") == "destination_suggestions":
            print(
                f"{label:<42} {'-':>4} {'-':>18} {'-':>6} {'-':>5} "
                f"{plan['season_status']:<12} {'-':>16}"
            )
            for suggestion in plan["suggestions"]:
                print(
                    f"  {suggestion['destination']}: Rs {suggestion['estimated_total']:,}, "
                    f"{suggestion['travel_time']} travel time"
                )
            continue
        transport_options = len(plan["options"]["trip_route"]) + len(plan["options"]["return"])
        print(
            f"{label:<42} {len(plan['route_legs']):>4} {transport_options:>18} "
            f"{plan['hotel_count']:>6} {len(plan['itinerary']):>5} "
            f"{plan['season_status']:<12} {plan['grand_total']:>16,.2f}"
        )
        for leg in plan["route_legs"]:
            times = (
                f"{leg['departure']}-{leg['arrival']} / {leg['duration']}"
                if leg.get("departure")
                else f"{leg['duration_hours']}h / estimate, not bookable"
            )
            print(
                f"  {leg['direction']}: {leg['from']} -> {leg['to']} "
                f"({leg['mode']}, {times}, group Rs {leg['group_total']:,})"
            )
        print(
            f"  season: {plan['season_status']}"
            + (f" - {plan['season_warning']['reason']}" if plan["season_warning"] else "")
        )
    print(f"\nVerified {len(CASES)} sample requests.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"TRIP PLANNER VERIFICATION FAILED: {error}", file=sys.stderr)
        raise
