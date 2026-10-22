import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useRef } from "react";
import { makeBookingQr } from "@/lib/qr";

const fmt = (value) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(value) || 0);
const DESTINATION_EXTRAS = {
  goa: {
    icon: "🏖️",
    packing: ["Light cotton clothes", "Sunscreen", "Reusable water bottle", "Comfortable sandals", "Swimwear", "Basic medicines"],
    tips: ["Use licensed taxis or app cabs.", "Carry water when exploring in the afternoon.", "Check local beach and event advisories."],
  },
  mumbai: {
    icon: "🌆",
    packing: ["Comfortable walking shoes", "Light rain jacket", "Reusable water bottle", "Power bank", "Basic medicines", "Small day bag"],
    tips: ["Allow extra time for city traffic.", "Use local transit for busy central areas.", "Follow venue entry and bag rules."],
  },
  delhi: {
    icon: "🏙️",
    packing: ["Comfortable walking shoes", "Reusable water bottle", "Sun protection", "Light layer", "Power bank", "Basic medicines"],
    tips: ["Check air quality before outdoor plans.", "Allow time for peak-hour traffic.", "Use official transit and ride services."],
  },
  bengaluru: {
    icon: "🌳",
    packing: ["Light layers", "Compact umbrella", "Comfortable shoes", "Reusable water bottle", "Power bank", "Basic medicines"],
    tips: ["Plan extra travel time for traffic.", "Carry a light rain layer.", "Confirm venue access before leaving."],
  },
};

function DonutChart({ items }) {
  const colors = ["#4f46e5", "#06b6d4", "#10b981", "#f59e0b", "#f43f5e", "#64748b"];
  const total = items.reduce((sum, item) => sum + item.amount, 0);
  let angle = -90;
  const slices = items.filter((item) => item.amount > 0).map((item, index) => {
    const span = total ? item.amount / total * 360 : 0;
    const start = angle * Math.PI / 180;
    const end = (angle + span) * Math.PI / 180;
    const largeArc = span > 180 ? 1 : 0;
    const path = `M 50 50 L ${50 + 42 * Math.cos(start)} ${50 + 42 * Math.sin(start)} A 42 42 0 ${largeArc} 1 ${50 + 42 * Math.cos(end)} ${50 + 42 * Math.sin(end)} Z`;
    angle += span;
    return <path key={item.label} d={path} fill={colors[index % colors.length]} />;
  });
  return (
    <div className="aura-print-chart">
      <svg viewBox="0 0 100 100" role="img" aria-label="Trip cost breakdown">{slices}<circle cx="50" cy="50" r="25" fill="white" /></svg>
      <ul>{items.map((item, index) => (
        <li key={item.label}><i style={{ backgroundColor: colors[index % colors.length] }} />{item.label}<strong>₹{fmt(item.amount)}</strong></li>
      ))}</ul>
    </div>
  );
}

function selectionFor(plan, selections, section) {
  const selected = selections?.[section]?.option;
  return selected || plan?.options?.[section]?.find((option) => option.recommended) || plan?.options?.[section]?.[0] || null;
}

function optionLabel(intent, option) {
  if (!option) return "Option not selected";
  if (intent === "flight") return `${option.airline || "Flight"} ${option.flight_no || ""}`.trim();
  if (intent === "train") return `${option.train_name || "Train"}${option.train_number ? ` · ${option.train_number}` : ""}`;
  if (intent === "hotel") return option.hotel || option.name || "Hotel";
  if (intent === "bus") return option.operator || "Bus";
  return option.event || option.match || option.name || "Selected option";
}

function PlanPrintDocument({ plan, selections = {}, rooms = 1, peopleNames = "", minimumTotal, receipts = [] }) {
  const generatedAt = useRef(new Date());
  const details = plan?.details || {};
  const event = plan?.kind === "event_travel";
  const destinationTrip = plan?.kind === "destination_trip";
  const travelers = Math.max(1, Number(details.travelers) || 1);
  const destination = event ? details.event_city : details.destination;
  const extras = DESTINATION_EXTRAS[String(destination || "").toLowerCase()] || {
    icon: "🧭",
    packing: ["Comfortable walking shoes", "Weather-appropriate clothes", "Reusable water bottle", "Power bank", "Travel documents", "Basic medicines"],
    tips: ["Check local weather before departure.", "Keep important documents secure.", "Use official transport services."],
  };
  const itinerary = plan?.itinerary || [];
  let costItems = [];
  let routeItems = [];
  let gst = 0;

  if (event) {
    const outbound = selections.outbound?.option || plan.options?.outbound?.find((option) => option.recommended) || plan.options?.outbound?.[0];
    const returning = selections.return?.option || plan.options?.return?.find((option) => option.recommended) || plan.options?.return?.[0];
    const hotel = selections.hotel?.option || plan.options?.hotel?.find((option) => option.recommended) || plan.options?.hotel?.[0];
    const ticket = selections.event?.option || plan.options?.event?.find((option) => option.recommended) || plan.options?.event?.[0];
    const local = selections.local?.option || plan.options?.local?.find((option) => option.recommended) || plan.options?.local?.[0];
    const gross = (price, count = 1) => Math.round(price * count * 1.18 * 100) / 100;
    costItems = [
      { label: "Travel", amount: (outbound?.price || 0) * travelers + (returning?.price || 0) * travelers },
      { label: "Stay", amount: (hotel?.price_per_night || 0) * rooms },
      { label: "Event", amount: (ticket?.price || 0) * travelers },
      { label: "Local transport", amount: (local?.price_per_day || 0) * (plan.local_days || 1) },
    ];
    gst = gross(outbound?.price || 0, travelers) - (outbound?.price || 0) * travelers
      + gross(returning?.price || 0, travelers) - (returning?.price || 0) * travelers
      + gross((hotel?.price_per_night || 0) * rooms) - (hotel?.price_per_night || 0) * rooms
      + gross(ticket?.price || 0, travelers) - (ticket?.price || 0) * travelers;
    routeItems = [
      { icon: outbound?.intent === "flight" ? "✈️" : outbound?.intent === "train" ? "🚆" : "🚌", title: `Travel · ${details.source} to ${destination}`, date: outbound?.travel_date || details.event_date, time: `${outbound?.departure || "—"} → ${outbound?.arrival || "—"}`, amount: gross(outbound?.price || 0, travelers), option: outbound },
      { icon: "🏨", title: `Stay · ${optionLabel("hotel", hotel)}`, date: `${details.event_date || ""} · 1 night`, time: "Hotel", amount: gross((hotel?.price_per_night || 0) * rooms), option: hotel },
      { icon: "🚕", title: `Local transport · ${local?.mode || "Estimate"}`, date: details.event_date, time: `${plan.local_days || 1} days · estimated`, amount: (local?.price_per_day || 0) * (plan.local_days || 1), option: local },
      { icon: "🎟️", title: `Event · ${optionLabel("event", ticket)}`, date: details.event_date, time: `${ticket?.departure || "—"}${ticket?.arrival ? `–${ticket.arrival}` : ""}`, amount: gross(ticket?.price || 0, travelers), option: ticket },
      { icon: returning?.intent === "flight" ? "✈️" : returning?.intent === "train" ? "🚆" : "🚌", title: `Return · ${destination} to ${details.source}`, date: returning?.travel_date || "", time: `${returning?.departure || "—"} → ${returning?.arrival || "—"}`, amount: gross(returning?.price || 0, travelers), option: returning },
    ];
  } else if (destinationTrip) {
    const costs = plan.cost_breakdown || {};
    costItems = [
      { label: "Transport", amount: costs.transport || 0 },
      { label: "Last-mile estimates", amount: costs.last_mile || 0 },
      { label: "Stay", amount: costs.stay || 0 },
      { label: "Daily food and local transport", amount: costs.daily || 0 },
      { label: "Taxes and fees", amount: costs.taxes_fees || 0 },
    ];
    routeItems = (plan.route_legs || []).map((leg, index) => {
      const selected = leg.direction === "return" ? selections.trip_return : selections.trip_transport;
      const option = leg.type === "transport" && selected?.intent === leg.mode ? selected.option : leg.option;
      const icon = leg.mode === "flight" ? "✈️" : leg.mode === "train" ? "🚆" : leg.mode === "bus" ? "🚌" : "🚕";
      return {
        icon,
        title: `${leg.direction === "return" ? "Return" : "Outbound"} · ${leg.from} to ${leg.to}${leg.type === "transport" ? ` · ${option?.airline || option?.train_name || option?.operator || leg.mode_label}` : " · estimate, not bookable"}`,
        date: option?.travel_date || option?.date || details.start_date || "",
        time: option
          ? `${option.departure || leg.departure || "—"} → ${option.arrival || leg.arrival || "—"} · ${option.duration || leg.duration || ""}`
          : `${leg.duration_hours || 0}h transfer`,
        amount: leg.type === "transport" && option
          ? option.price * (Number(details.travelers) || 1)
          : leg.group_total || 0,
        option,
        key: `${leg.direction}-${leg.type}-${leg.mode}-${index}`,
      };
    });
  } else {
    const transportIntent = selections.flight?.option
      ? "flight"
      : selections.train?.option
        ? "train"
        : selections.bus?.option
          ? "bus"
          : (plan.sections || []).find((section) => ["flight", "train", "bus"].includes(section));
    const transport = selectionFor(plan, selections, transportIntent);
    const hotel = selectionFor(plan, selections, "hotel");
    const local = plan.local_transport?.[0];
    costItems = [
      { label: "Travel", amount: transport ? transport.price * travelers : 0 },
      { label: "Stay", amount: hotel ? hotel.price_per_night * (details.nights || 3) * rooms : 0 },
      { label: "Local transport", amount: local ? local.price_per_day * ((details.nights || 3) + 1) : 0 },
    ];
    if (transport) {
      routeItems.push({
        icon: transportIntent === "train" ? "🚆" : "✈️",
        title: `${optionLabel(transportIntent, transport)} · ${details.source} to ${destination}`,
        date: details.start_date,
        time: `${transport.departure || "—"} → ${transport.arrival || "—"} · ${transport.duration || ""}`,
        amount: transport.price * travelers,
        option: transport,
      });
    }
    if (hotel) routeItems.push({ icon: "🏨", title: `Stay · ${optionLabel("hotel", hotel)}`, date: `${details.nights || 3} nights`, time: `${hotel.stars ? `${hotel.stars} star` : hotel.room_type || "Hotel"}`, amount: hotel.price_per_night * (details.nights || 3) * rooms, option: hotel });
    if (local) routeItems.push({ icon: "🚕", title: "Local transport estimate", date: `${(details.nights || 3) + 1} days`, time: "Estimated", amount: local.price_per_day * ((details.nights || 3) + 1), option: local });
  }

  const taxesFees = destinationTrip ? Number(plan.cost_breakdown?.taxes_fees) || 0 : 0;
  const base = destinationTrip
    ? costItems.filter((item) => item.label !== "Taxes and fees").reduce((sum, item) => sum + item.amount, 0)
    : costItems.reduce((sum, item) => sum + item.amount, 0);
  const total = destinationTrip ? Number(plan.grand_total ?? plan.cost_breakdown?.total ?? base) : base + gst;
  const budget = Number(details.budget) || 0;
  const perPerson = travelers > 1 ? Math.ceil(total / travelers) : total;
  const spendItems = destinationTrip
    ? costItems
    : [...costItems, ...(gst > 0 ? [{ label: "Taxes & fees", amount: gst }] : [])];
  const allReceipts = [...(plan.bookings || []), ...receipts].filter((item, index, list) => item?.booking_id && list.findIndex((entry) => entry.booking_id === item.booking_id) === index);
  const title = event ? `${details.event || "Event"} · ${destination}` : `${destination || "Trip"} Escape`;
  const planId = useRef(`AURA-PLAN-${generatedAt.current.getTime().toString(36).toUpperCase()}`);
  const generated = generatedAt.current.toLocaleString("en-IN");

  return (
    <div className="aura-print-document" aria-hidden="true">
      <div className="aura-print-page aura-print-cover">
        <header className="aura-print-header">
          <div className="aura-print-brand"><span className="aura-print-logo">A</span><span><strong>AURA</strong><small>Autonomous Universal Resource Agent</small></span></div>
          <span className="aura-print-label">YOUR TRAVEL PLAN</span>
        </header>
        <div className="aura-print-banner">
          <span className="aura-print-theme">{extras.icon}</span>
          <p className="aura-print-eyebrow">PERSONALIZED MOCK TRAVEL PLAN</p>
          <h1>{title}, {travelers} traveler{travelers === 1 ? "" : "s"}</h1>
          <p>{event ? `${details.event_date || "Event date"} · ${details.source || "Source"} → ${destination || "Destination"}` : `${details.start_date || "Start date"} · ${details.source || "Source"} → ${destination || "Destination"} · ${details.nights || 3} nights`}</p>
          <div className="aura-print-planid"><span>Plan ID <strong>{planId.current}</strong></span><span>Generated <strong>{generated}</strong></span></div>
        </div>
        <h2>Journey at a glance</h2>
        <div className="aura-print-route">
          {routeItems.map((item, index) => (
            <div className="aura-print-route-item" key={`${item.title}-${index}`}>
              <span className="aura-print-route-icon">{item.icon}</span>
              <span className="aura-print-route-line" />
              <div><strong>{item.title}</strong><small>{item.date} · {item.time}</small></div>
              <b>₹{fmt(item.amount)}</b>
            </div>
          ))}
        </div>
        <div className="aura-print-overview">
          <div>
            <h2>Cost overview</h2>
            <DonutChart items={spendItems} />
          </div>
          <div className="aura-print-budget">
            <h2>Budget check</h2>
            {budget > 0 ? <>
              <p>Estimated total <strong>₹{fmt(total)}</strong></p>
              <div className="aura-print-budget-track"><span className={total > budget ? "over" : ""} style={{ width: `${Math.min(100, (total / budget) * 100)}%` }} /></div>
              <p>{total > budget ? `Over budget by ₹${fmt(total - budget)}` : `₹${fmt(budget - total)} remaining of ₹${fmt(budget)}`}</p>
              {total > budget && <small>{(minimumTotal ?? plan.budget_status?.minimum_needed) != null ? `Minimum available estimate: ₹${fmt(minimumTotal ?? plan.budget_status.minimum_needed)}.` : "Minimum estimate unavailable."} Consider the Budget tier or a lower-cost travel mode.</small>}
            </> : <p>No budget set · estimated total <strong>₹{fmt(total)}</strong></p>}
            <table className="aura-print-fare-table"><tbody>
              <tr><td>Base fare & estimated costs</td><td>₹{fmt(base)}</td></tr>
              <tr><td>Taxes and fees</td><td>₹{fmt(taxesFees)}</td></tr>
              <tr><td>GST (18% where applicable)</td><td>₹{fmt(gst)}</td></tr>
              <tr><td>Discount</td><td>₹0</td></tr>
              <tr className="aura-print-grand"><td>Grand total</td><td>₹{fmt(total)}</td></tr>
            </tbody></table>
          </div>
        </div>
        {travelers > 1 && (
          <div className="aura-print-split">
            <h2>Split the cost</h2>
            <strong>Each person pays ₹{fmt(perPerson)}</strong>
            <p>Total ₹{fmt(total)} · {travelers} people</p>
            <div>{Array.from({ length: travelers }, (_, index) => {
              const name = peopleNames.split(",").map((person) => person.trim()).filter(Boolean)[index] || `Person ${index + 1}`;
              return <span key={index}>{name} <b>₹{fmt(perPerson)}</b></span>;
            })}</div>
          </div>
        )}
      </div>

      <div className="aura-print-page">
        <header className="aura-print-section-header"><span className="aura-print-logo">A</span><div><strong>{title}</strong><small>{destinationTrip ? "Trip details" : "Visual itinerary"} · {details.source} → {destination}</small></div></header>
        {destinationTrip && plan.season_warning && (
          <aside className="aura-print-season-warning">
            <strong>Season warning · {plan.season_warning.month}</strong>
            <p>{plan.season_warning.reason}</p>
          </aside>
        )}
        {!destinationTrip && (
          <>
            <h1>Day-by-day itinerary</h1>
            {itinerary.length > 0 ? itinerary.map((day) => (
              <article className="aura-print-day" key={`${day.day}-${day.date}`}>
                <span>DAY {day.day}{day.travel_day ? " · TRAVEL DAY" : ""}</span><small>{day.date}</small>
                {day.activities?.length
                  ? <ul>{day.activities.map((activity, index) => <li key={`${activity.attraction}-${index}`}>{activity.time} · {activity.attraction}</li>)}</ul>
                  : <p>{day.activity}</p>}
                {day.daily_estimate != null && <small>Food and local transport estimate: ₹{fmt(day.daily_estimate)}</small>}
              </article>
            )) : routeItems.map((item, index) => (
              <article className="aura-print-day" key={item.title}><span>STEP {index + 1} · {item.icon}</span><small>{item.date}</small><p>{item.title} · {item.time}</p></article>
            ))}
          </>
        )}
        <div className="aura-print-recommendations">
          <h2>Why we picked these options</h2>
          {routeItems.map((item, index) => {
              const selectedOption = item.option || (event ? [
                selections.outbound?.option || plan.options?.outbound?.find((option) => option.recommended),
                selections.hotel?.option || plan.options?.hotel?.find((option) => option.recommended),
                null,
                selections.event?.option || plan.options?.event?.find((option) => option.recommended),
                selections.return?.option || plan.options?.return?.find((option) => option.recommended),
              ][index] : null);
              return selectedOption?.reason ? <p key={item.title}><strong>{item.title}:</strong> {selectedOption.reason}</p> : null;
            })}
        </div>
        <div className="aura-print-extras">
          <section><h2>Packing checklist</h2>{extras.packing.map((item) => <p key={item}>□ {item}</p>)}</section>
          <section><h2>Local tips</h2>{extras.tips.map((tip) => <p key={tip}>• {tip}</p>)}</section>
        </div>
        <aside className="aura-print-contacts"><strong>Important contacts</strong><span>Emergency: 112</span><span>Tourist helpline: 1363</span></aside>
      </div>

      {allReceipts.length > 0 && (
        <div className="aura-print-page aura-print-bookings">
          <header className="aura-print-section-header"><span className="aura-print-logo">A</span><div><strong>{title}</strong><small>Simulated booking summary</small></div></header>
          <h1>Booking summary</h1>
          {allReceipts.map((booking) => (
            <article className="aura-print-booking" key={booking.booking_id}>
              <div><span className="aura-print-label">BOOKING ID</span><strong>{booking.booking_id}</strong></div>
              <p>PNR: {booking.pnr || "Not assigned (simulated)"} · Transaction ID: {booking.transaction_id || "Not applicable (simulated)"}</p>
              <p>{optionLabel(booking.intent, booking.option)} · ₹{fmt(booking.amount?.total)}</p>
              <div className="aura-print-qr" aria-label="Booking ID QR code">
                <svg viewBox="0 0 21 21" role="img" aria-label={`QR placeholder for ${booking.booking_id}`}>
                  {makeBookingQr(booking.booking_id).flatMap((row, y) => row.map((on, x) => on && <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" fill="#172554" />))}
                </svg>
                <small>BOOKING ID QR</small>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PlanPrintAction(props) {
  return (
    <>
      <Button variant="outline" onClick={() => window.print()} className="aura-screen-only">
        <Download className="w-4 h-4 mr-1.5" /> Download plan (PDF)
      </Button>
      <PlanPrintDocument {...props} />
    </>
  );
}
