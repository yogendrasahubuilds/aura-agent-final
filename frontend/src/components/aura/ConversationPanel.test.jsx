import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ConversationPanel from "./ConversationPanel";

jest.mock("@/components/aura/BookingReceipt", () => function MockBookingReceipt() {
  return <div data-testid="booking-receipt">Booking Confirmed</div>;
});

describe("ConversationPanel result rendering", () => {
  it("renders tool results and the booking review exactly once", () => {
    const hotel = {
      id: "HTL-1",
      hotel: "Marine Drive Comfort Stay",
      category: "3-star",
      room_type: "Deluxe Room",
      rating: 4.5,
      price_per_night: 3500,
      rooms_available: 4,
      tier: "Comfort",
    };
    const local = {
      id: "LOC-1",
      mode: "Metro",
      city: "Mumbai",
      destination: "Mumbai",
      price_per_day: 400,
    };
    const tripPlan = {
      plan_id: "run-1",
      kind: "tool_results",
      details: {
        city: "Mumbai",
        start_date: "2026-10-28",
        nights: 3,
        travelers: 4,
      },
      sections: ["hotel", "local_transport", "hotel"],
      options: {
        hotel: [hotel, hotel],
        local_transport: [local, local],
      },
      local_transport: [local],
      local_transport_days: 4,
    };
    const preview = {
      amount: {
        subtotal: 10000,
        fees: 0,
        discount: 0,
        tax: 500,
        total: 10500,
        breakdown: [],
        gst_rate: 5,
      },
    };
    const markup = renderToStaticMarkup(
      <ConversationPanel
        messages={[]}
        user={{}}
        input=""
        onInputChange={() => {}}
        onSend={() => {}}
        onReset={() => {}}
        loading={false}
        speechSupported={false}
        listening={false}
        onVoiceInput={() => {}}
        tripPlan={tripPlan}
        approved
        selections={{ hotel: { intent: "hotel", option: hotel } }}
        onSelectOption={() => {}}
        selection={{ intent: "hotel", option: hotel }}
        preview={preview}
        quantity={4}
        nights={3}
        rooms={2}
        onRoomsChange={() => {}}
        onConfirm={() => {}}
        onCancelSelection={() => {}}
      />,
    );

    expect(markup.match(/data-testid="chat-tool-results"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="confirmation-card"/g)).toHaveLength(1);
    expect(markup).not.toContain('data-testid="trip-plan"');
    expect(markup.match(/<h4[^>]*>Hotels<\/h4>/g)).toHaveLength(1);
    expect(markup.match(/<h4[^>]*>Local transport<\/h4>/g)).toHaveLength(1);
    expect(markup.match(/>Traveler details<\/h4>/g)).toHaveLength(1);
    expect(markup.match(/>Simulated payment<\/h4>/g)).toHaveLength(1);
    expect(markup.match(/Journey at a glance/g)).toHaveLength(1);
    expect(markup.match(/Download plan \(PDF\)/g)).toHaveLength(1);
  });

  it("renders a group trip, split, and shared booking review once", () => {
    const flight = {
      id: "FLT-1",
      airline: "IndiGo",
      flight_no: "6E-101",
      source: "Delhi",
      destination: "Goa",
      departure: "08:00",
      arrival: "10:30",
      duration: "2h 30m",
      class: "Economy",
      price: 5000,
      seats_available: 20,
      recommended: true,
    };
    const hotel = {
      id: "HTL-2",
      hotel: "Goa Comfort Stay",
      room_type: "Deluxe Room",
      price_per_night: 3000,
      rooms_available: 5,
      rating: 4.5,
      recommended: true,
    };
    const local = { id: "LOC-2", mode: "Taxi", city: "Goa", price_per_day: 1200 };
    const tripPlan = {
      plan_id: "run-2",
      kind: "trip",
      details: {
        source: "Delhi",
        destination: "Goa",
        start_date: "2026-10-20",
        nights: 3,
        travelers: 4,
        budget: null,
      },
      sections: ["flight", "hotel", "local_transport"],
      options: { flight: [flight], hotel: [hotel], local_transport: [local] },
      local_transport: [local],
      itinerary: [],
    };
    const markup = renderToStaticMarkup(
      <ConversationPanel
        messages={[]}
        user={{}}
        input=""
        onInputChange={() => {}}
        onSend={() => {}}
        onReset={() => {}}
        loading={false}
        speechSupported={false}
        listening={false}
        onVoiceInput={() => {}}
        tripPlan={tripPlan}
        approved
        selections={{ flight: { intent: "flight", option: flight } }}
        onSelectOption={() => {}}
        selection={{ intent: "flight", option: flight }}
        preview={{ amount: { total: 10000, breakdown: [] } }}
        quantity={4}
        nights={3}
        rooms={2}
        onRoomsChange={() => {}}
        onConfirm={() => {}}
        onCancelSelection={() => {}}
      />,
    );

    expect(markup.match(/data-testid="trip-plan"/g)).toHaveLength(1);
    expect(markup).not.toContain('data-testid="chat-tool-results"');
    expect(markup.match(/data-testid="group-split-card"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="confirmation-card"/g)).toHaveLength(1);
    expect(markup.match(/>Simulated payment<\/h4>/g)).toHaveLength(1);
  });

  it("renders the destination trip sections and PDF route once", () => {
    const flight = {
      id: "FLT-DEST-1",
      intent: "flight",
      airline: "IndiGo",
      flight_no: "6E-101",
      source: "Raipur",
      destination: "Delhi",
      departure: "08:00",
      arrival: "10:00",
      duration: "2h",
      class: "Economy",
      price: 5000,
      seats_available: 18,
      tier: "Comfort",
      recommended: true,
      reason: "Best value based on the available price and quality.",
    };
    const returning = { ...flight, id: "FLT-DEST-2", source: "Delhi", destination: "Raipur" };
    const train = {
      id: "TRN-DEST-1",
      intent: "train",
      train_name: "AURA Simulated Express",
      train_number: "SIM-101",
      source: "Raipur",
      destination: "Chandigarh",
      departure: "12:30",
      arrival: "05:12",
      duration: "16h 42m",
      class: "3A",
      price: 2400,
      seats_available: 56,
      tier: "Comfort",
      reason: "Available train option.",
    };
    const hotel = {
      id: "DST-HTL-1",
      hotel: "Hillview Fictional Stay",
      name: "Hillview Fictional Stay",
      category: "3-star",
      room_type: "Deluxe Room",
      rating: 4.5,
      stars: 3,
      location: "Old Town",
      price_per_night: 3000,
      rooms_available: 4,
      tier: "Comfort",
      recommended: true,
    };
    const checkoutItem = {
      intent: "flight",
      option: flight,
      quantity: 2,
      nights: 1,
      rooms: 1,
      label: "Outbound travel",
      preview: { amount: { subtotal: 10000, fees: 0, tax: 1800, total: 11800, breakdown: [] } },
    };
    const tripPlan = {
      plan_id: "destination-run-1",
      kind: "destination_trip",
      details: {
        source: "Raipur",
        destination: "Manali",
        start_date: "2026-10-20",
        nights: 3,
        travelers: 2,
        budget: 50000,
      },
      sections: ["trip_route", "hotel", "itinerary", "cost_breakdown"],
      options: {
        trip_route: [train],
        flight: [flight],
        flight_return: [returning],
        train: [train],
        train_return: [{ ...train, id: "TRN-DEST-2", source: "Chandigarh", destination: "Raipur" }],
        hotel: [hotel],
      },
      selected_defaults: {
        transport: train,
        return: { ...train, id: "TRN-DEST-2", source: "Chandigarh", destination: "Raipur" },
        return: returning,
        hotel,
      },
      route_legs: [
        { type: "transport", direction: "outbound", mode: "flight", mode_label: "Flight", from: "Raipur", to: "Delhi", departure: "08:00", arrival: "10:00", duration: "2h", group_total: 10000, bookable: true, option: flight },
        { type: "transfer", direction: "outbound", mode: "bus", from: "Delhi", to: "Manali", duration_hours: 8, distance_km: 500, group_total: 2000, estimate_only: true, bookable: false },
        { type: "transport", direction: "return", mode: "flight", mode_label: "Flight", from: "Delhi", to: "Raipur", departure: "11:00", arrival: "13:00", duration: "2h", group_total: 10000, bookable: true, option: returning },
      ],
      route_duration_minutes: 600,
      itinerary: [{
        day: 1,
        date: "2026-10-20",
        travel_day: true,
        activities: [{ attraction: "Old Manali", time: "14:00" }],
        daily_estimate: 1000,
      }],
      season_status: "in_season",
      season_warning: { destination: "Manali", month: "October", reason: "Simulated seasonal note." },
      season_alternatives: [],
      cost_breakdown: { transport: 20000, last_mile: 2000, stay: 9000, daily: 3000, taxes_fees: 2000, total: 36000 },
      grand_total: 36000,
      per_person: 18000,
      budget_status: { budget: 50000, remaining: 14000, over_budget: false },
      rooms: 1,
    };
    const markup = renderToStaticMarkup(
      <ConversationPanel
        messages={[]}
        user={{ name: "Test Traveler", email: "test@example.com" }}
        input=""
        onInputChange={() => {}}
        onSend={() => {}}
        onReset={() => {}}
        loading={false}
        speechSupported={false}
        listening={false}
        onVoiceInput={() => {}}
        tripPlan={tripPlan}
        approved={false}
        selections={{
          trip_transport: { intent: "train", option: train },
          trip_return: { intent: "train", option: { ...train, id: "TRN-DEST-2", source: "Chandigarh", destination: "Raipur" } },
          hotel: { intent: "hotel", option: hotel },
        }}
        onSelectOption={() => {}}
        onTripOptionSelect={() => {}}
        quantity={2}
        nights={3}
        rooms={1}
        onRoomsChange={() => {}}
        onConfirm={() => {}}
        onCancelSelection={() => {}}
        eventCheckout={{
          items: [checkoutItem],
          preview: { amount: { subtotal: 10000, fees: 0, tax: 1800, total: 11800, breakdown: [] } },
        }}
        eventPlanStatus="idle"
        eventBookings={[]}
        onOpenEventCheckout={() => {}}
        onEventPricingChange={() => {}}
        onBookEventPlan={() => {}}
        onCancelEventCheckout={() => {}}
        onNextBooking={() => {}}
      />,
    );

    expect(markup.match(/data-testid="destination-trip-plan"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="destination-route"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="destination-stay"/g)).toHaveLength(1);
    expect(markup).not.toContain('data-testid="destination-itinerary"');
    expect(markup.match(/data-testid="destination-cost-breakdown"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="trip-season-warning"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="trip-flight-options"/g)).toHaveLength(1);
    expect(markup.match(/data-testid="trip-train-options"/g)).toHaveLength(1);
    expect(markup).toContain("Flights");
    expect(markup).toContain("IndiGo 6E-101");
    expect(markup).toContain("Trains");
    expect(markup.match(/data-testid="confirmation-card"/g)).toHaveLength(1);
    expect(markup.match(/Journey at a glance/g)).toHaveLength(1);
    expect(markup.match(/class="aura-print-route-item"/g)).toHaveLength(3);
    expect(markup).not.toContain('class="aura-print-day"');
    expect(markup).not.toContain("Day-by-day itinerary");
    expect(markup.match(/class="aura-print-season-warning"/g)).toHaveLength(1);
    expect(markup).not.toContain("Old Manali");
    expect(markup).toContain("Simulated seasonal note.");
    expect(markup).toContain("Estimate · not bookable");
  });
});
