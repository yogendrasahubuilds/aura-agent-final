import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { MapPin, Mic, MicOff, RefreshCw, Send, Plane, Train, Hotel, Bus, Music, Trophy } from "lucide-react";
import ConfirmationCard from "@/components/aura/ConfirmationCard";
import BookingReceipt from "@/components/aura/BookingReceipt";
import GroupSplitCard from "@/components/aura/GroupSplitCard";
import PlanPrintAction from "@/components/aura/PlanPrintDocument";

const fmt = (value) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(value || 0);
const uniqueById = (options = []) => {
  const seen = new Set();
  return options.filter((option) => {
    if (!option?.id) return true;
    if (seen.has(option.id)) return false;
    seen.add(option.id);
    return true;
  });
};
const uniqueSections = (sections = []) => [...new Set(sections)];
const itemName = (tool, option) => (
  tool === "flight"
    ? `${option.airline} ${option.flight_no}`
    : tool === "train"
      ? `${option.train_name} · ${option.train_no}`
      : tool === "bus"
        ? `${option.operator} · ${option.bus_no}`
        : tool === "hotel"
          ? option.hotel
          : option.match || option.event
);
const grossEstimate = (unit, quantity = 1) => Math.round(unit * quantity * 1.18 * 100) / 100;
const eventOptionName = (intent, option) => (
  intent === "flight"
    ? `${option.airline} ${option.flight_no}`
    : intent === "train"
      ? `${option.train_name} ${option.train_no}`
      : intent === "bus"
        ? `${option.operator} ${option.bus_no}`
        : intent === "hotel"
          ? option.hotel
          : option.match || option.event || option.mode
);

function EventOptionGroup({ part, title, options, selected, travelers, localDays, rooms = 1, tradeoff, onSelect }) {
  const Icon = part === "event" ? (options[0]?.match ? Trophy : Music)
    : part === "hotel" ? Hotel
      : part === "local" ? MapPin
        : part === "return" ? (selected?.intent === "flight" ? Plane : selected?.intent === "train" ? Train : Bus)
          : (options[0]?.intent === "flight" ? Plane : options[0]?.intent === "train" ? Train : Bus);

  return (
    <section className="space-y-2">
      <h4 className="font-heading font-bold text-slate-900">{title}</h4>
      {tradeoff && <p className="text-xs text-slate-600">{tradeoff}</p>}
      <div className="space-y-2">
        {uniqueById(options).map((option) => {
          const intent = part === "event" ? (option.match ? "cricket" : "concert")
            : part === "hotel" ? "hotel"
              : part === "local" ? "local_transport" : option.intent;
          const unit = part === "hotel" ? option.price_per_night
            : part === "local" ? option.price_per_day * localDays : option.price;
          const quantity = part === "hotel" ? rooms : part === "local" ? 1 : travelers;
          const chosen = selected?.intent === intent && selected?.option.id === option.id;
          const time = part === "hotel"
            ? `${option.room_type} · ${option.rating} ★ · ${option.location}`
            : part === "local"
              ? `${option.mode} · ${localDays} days`
              : `${option.travel_date || option.date || ""} · ${option.departure}–${option.arrival} · ${option.duration || ""}`;
          return (
            <Card key={`${intent}-${option.id}`} className={`p-3 bg-white border ${chosen ? "border-indigo-500 ring-2 ring-indigo-100" : "border-slate-200"}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-sm text-slate-900 flex items-center gap-1.5">
                    <Icon className="w-4 h-4 shrink-0 text-indigo-600" />
                    {eventOptionName(intent, option)}
                  </p>
                  {option.tier && <Badge variant="outline" className="mt-1">{option.tier}</Badge>}
                  {option.recommended && <Badge className="ml-1 mt-1 bg-indigo-100 text-indigo-800 border border-indigo-200">Recommended</Badge>}
                  <p className="text-xs text-slate-500 mt-1">
                    {part === "event" ? `${option.stadium || option.venue} · ${option.city} · ` : ""}
                    {part === "outbound" || part === "return" ? `${option.source} → ${option.destination} · ` : ""}
                    {time}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {part === "hotel"
                      ? `${option.rooms_available} rooms · 1 night`
                      : part === "local"
                        ? "Estimated mock local transport"
                        : `${option.seats_available} seats left`}
                  </p>
                  {option.reason && <p className="text-xs text-indigo-700 mt-1">{option.reason}</p>}
                </div>
                <div className="text-right shrink-0">
                  <p className="font-bold text-sm text-slate-900">
                    ₹{fmt(part === "local" ? unit : grossEstimate(unit, quantity))}
                  </p>
                  <p className="text-[11px] text-slate-500">{part === "local" ? "trip estimate" : "group estimate incl. 18% GST"}</p>
                </div>
              </div>
              <div className="flex justify-end mt-2">
                <Button size="sm" variant={chosen ? "default" : "outline"} onClick={() => onSelect(part, { intent, option })}>
                  {chosen ? "Selected" : "Select"}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

function OptionCard({ tool, option, details, selected, onSelect, rooms = 1 }) {
  const nightsTotal = (option.price_per_night || 0) * details.nights;
  const groupTotal = tool === "hotel"
    ? nightsTotal * rooms
    : (option.price || 0) * details.travelers;
  const Icon = tool === "flight" ? Plane : tool === "train" ? Train : Hotel;

  return (
    <Card className={`p-4 bg-white border ${selected ? "border-indigo-500 ring-2 ring-indigo-100" : "border-slate-200"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-heading font-bold text-slate-900 flex items-center gap-1.5">
            <Icon className="w-4 h-4 text-indigo-600" />{itemName(tool, option)}
          </p>
          <Badge variant="outline" className="mt-1">{option.tier}</Badge>
          {option.recommended && <Badge className="ml-1 mt-1 bg-indigo-100 text-indigo-800 border border-indigo-200">Recommended</Badge>}
          {tool === "hotel" ? (
            <p className="text-xs text-slate-500 mt-2">{option.room_type} · {option.rating} ★ · {option.location}</p>
          ) : (
            <p className="text-xs text-slate-500 mt-2">{option.class} · {option.departure}–{option.arrival} · {option.duration}</p>
          )}
        </div>
        <div className="text-right shrink-0">
          {tool === "hotel" ? (
            <>
              <p className="font-bold text-slate-900">₹{fmt(option.price_per_night)} / night</p>
              <p className="text-xs text-slate-500">{details.nights} nights · {rooms} room{rooms === 1 ? "" : "s"} · group total ₹{fmt(groupTotal)}</p>
            </>
          ) : (
            <>
              <p className="font-bold text-slate-900">₹{fmt(option.price)} / person</p>
              <p className="text-xs text-slate-500">group total ₹{fmt(groupTotal)}</p>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        <p className="text-xs text-slate-500">
          {tool === "hotel" ? `${option.rooms_available} rooms available` : `${option.seats_available} seats left`}
        </p>
        <Button size="sm" variant={selected ? "default" : "outline"} onClick={() => onSelect(option, tool)}>
          {selected ? "Selected" : "Select"}
        </Button>
      </div>
      {option.reason && <p className="text-xs text-indigo-700 mt-2">{option.reason}</p>}
    </Card>
  );
}

function LocalTransportCard({ option, days }) {
  return (
    <Card className="p-4 bg-white border-slate-200">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-heading font-bold text-slate-900">{option.mode}</p>
          <p className="text-xs text-slate-500 mt-1">{option.city} · estimated for {days} days</p>
          {option.reason && <p className="text-xs text-indigo-700 mt-2">{option.reason}</p>}
        </div>
        <div className="text-right shrink-0">
          <p className="font-bold text-slate-900">₹{fmt(option.price_per_day)} / day</p>
          <p className="text-xs text-slate-500">₹{fmt(option.price_per_day * days)} estimated total</p>
        </div>
      </div>
    </Card>
  );
}

function DestinationTripPanel({
  plan,
  selections,
  rooms,
  travelerNames,
  onNamesChange,
  onRoomsChange,
  onSend,
  onSelectOption,
  loading,
  user,
  approved,
  checkout,
  status,
  error,
  bookings,
  onOpenCheckout,
  onPricingChange,
  onConfirm,
  onCancelCheckout,
  onNextBooking,
}) {
  const details = plan.details || {};
  const travelers = Math.max(1, Number(details.travelers) || 1);
  const destination = details.destination;
  const cost = plan.cost_breakdown || {};
  const transport = selections.trip_transport || (plan.selected_defaults?.transport
    ? { intent: plan.selected_defaults.transport.intent, option: plan.selected_defaults.transport }
    : null);
  const returning = selections.trip_return || (plan.selected_defaults?.return
    ? { intent: plan.selected_defaults.return.intent, option: plan.selected_defaults.return }
    : null);
  const hotel = selections.hotel || { intent: "hotel", option: plan.selected_defaults?.hotel };
  const transportOptionGroups = ["flight", "train", "bus"].map((mode) => ({
    mode,
    options: uniqueById(
      plan.options?.[mode]?.length
        ? plan.options[mode]
        : (plan.options?.trip_route || []).filter((option) => option.intent === mode),
    ),
  })).filter((group) => group.options.length > 0);
  const hotelOptions = uniqueById(plan.options?.hotel || []);
  const minimumNeeded = plan.budget_status?.minimum_needed;
  const modeIcon = (mode) => mode === "flight" ? Plane : mode === "train" ? Train : mode === "bus" ? Bus : MapPin;
  const modeLabel = (mode) => ({ flight: "Flights", train: "Trains", bus: "Buses" })[mode] || mode;
  const displayName = (intent, option) => intent === "flight"
    ? `${option.airline} ${option.flight_no}`
    : intent === "train"
      ? `${option.train_name} · ${option.train_number || option.train_no || ""}`
      : `${option.operator || "Bus"} · ${option.bus_no || ""}`;
  const optionButton = (part, option, intent) => (
    <Button
      size="sm"
      variant={(part === "trip_transport" ? transport : hotel)?.option?.id === option.id ? "default" : "outline"}
      onClick={() => onSelectOption(part, option, intent)}
      aria-label={`Select ${option.tier} ${part === "hotel" ? "hotel" : intent}`}
    >
      {(part === "trip_transport" ? transport : hotel)?.option?.id === option.id ? "Selected" : "Select"}
    </Button>
  );

  if (plan.kind === "destination_suggestions") {
    return (
      <Card className="p-5 bg-white border-indigo-200 space-y-4" data-testid="destination-suggestions">
        <h3 className="font-heading text-lg font-bold text-slate-900">Destinations for your trip</h3>
        <p className="text-sm text-slate-600">In-season choices matching {details.theme}{details.budget ? ` within ₹${fmt(details.budget)}` : ""}.</p>
        {plan.suggestions?.map((suggestion) => (
          <Card key={suggestion.id} className="p-4 bg-white border-slate-200">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="font-semibold text-slate-900">{suggestion.destination} · {suggestion.state}</h4>
                <p className="text-xs text-slate-600 mt-1">{(suggestion.themes || []).join(" · ")}</p>
                <p className="text-xs text-slate-600 mt-1">Estimated travel time: {suggestion.travel_time}</p>
              </div>
              <p className="font-bold text-slate-900 shrink-0">₹{fmt(suggestion.estimated_total)}</p>
            </div>
            <div className="mt-3 flex justify-end">
              <Button size="sm" onClick={() => onSend(suggestion.select_message)} className="bg-indigo-600 hover:bg-indigo-700 text-white">Select destination</Button>
            </div>
          </Card>
        ))}
      </Card>
    );
  }

  if (plan.kind === "destination_trip_unavailable") {
    return (
      <Card className="p-5 bg-white border-amber-200 space-y-2" data-testid="destination-trip-unavailable">
        <h3 className="font-heading text-lg font-bold text-slate-900">No route found</h3>
        <p className="text-sm text-slate-700">{plan.error}</p>
        {plan.nearest_alternative_city && <p className="text-sm text-slate-600">Nearest configured alternative: {plan.nearest_alternative_city}.</p>}
      </Card>
    );
  }

  const routeLegs = plan.route_legs || [];
  const costRows = [
    ["Transport", cost.transport],
    ["Last-mile estimates", cost.last_mile],
    [`Stay · ${details.nights} nights`, cost.stay],
    ["Daily food and local transport", cost.daily],
    ["Taxes and fees", cost.taxes_fees],
  ].filter(([, amount]) => Number(amount) > 0);
  const splitLines = [
    ["Transport", cost.transport, false],
    ["Stay", cost.stay, true],
    ["Last-mile estimate", cost.last_mile, true],
    ["Daily costs", cost.daily, true],
    ["Taxes and fees", cost.taxes_fees, true],
  ].filter(([, amount]) => Number(amount) > 0).map(([label, amount, shared]) => ({
    label,
    total: Number(amount),
    perPerson: shared ? 0 : Number(amount) / travelers,
    shared,
  }));
  const grandTotal = Number(plan.grand_total ?? cost.total ?? 0);
  const budget = Number(details.budget) || 0;

  return (
    <Card className="p-5 bg-white border-indigo-200 space-y-5" data-testid="destination-trip-plan">
      <div className="flex justify-end">
        <PlanPrintAction
          plan={plan}
          selections={selections}
          rooms={rooms}
          peopleNames={travelerNames}
          minimumTotal={minimumNeeded}
          receipts={bookings}
        />
      </div>
      <header>
        <h3 className="font-heading text-lg font-bold text-slate-900">Your trip plan</h3>
        <p className="text-sm text-slate-600">
          {details.source} → {destination} · {details.start_date} · {details.nights} nights · {travelers} traveler{travelers === 1 ? "" : "s"}
        </p>
      </header>

      {plan.season_warning && (
        <section className="rounded-lg border border-amber-300 bg-amber-50 p-4" data-testid="trip-season-warning">
          <h4 className="font-heading font-bold text-amber-950">Season warning · {plan.season_warning.month}</h4>
          <p className="mt-1 text-sm text-amber-900">{plan.season_warning.reason}</p>
          {plan.season_alternatives?.length > 0 && (
            <div className="mt-3 space-y-2">
              <p className="text-sm font-semibold text-amber-950">In-season alternatives</p>
              {plan.season_alternatives.slice(0, 3).map((alternative) => (
                <div key={alternative.id} className="flex items-center justify-between gap-3 text-sm">
                  <span>{alternative.destination} · estimated ₹{fmt(alternative.estimated_total)}</span>
                  <Button size="sm" variant="outline" onClick={() => onSend(`Plan a trip to ${alternative.destination} from ${details.source} starting ${details.start_date}`)}>Select</Button>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="space-y-3" data-testid="destination-route">
        <h4 className="font-heading font-bold text-slate-900">Door-to-door route</h4>
        <ol className="space-y-3 border-l-2 border-indigo-100 pl-4">
          {routeLegs.map((leg, index) => {
            const selected = leg.direction === "return" ? returning : transport;
            const option = leg.type === "transport" && selected?.option ? selected.option : leg.option;
            const mode = leg.type === "transport" && selected?.intent ? selected.intent : leg.mode;
            const Icon = modeIcon(mode);
            return (
              <li key={`${leg.direction}-${leg.type}-${leg.mode}-${index}`} className="relative">
                <div className="flex items-start gap-3">
                  <Icon className="w-4 h-4 mt-1 text-indigo-600 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-sm text-slate-900">
                      {option?.source || leg.from} → {option?.destination || leg.to} · {mode[0].toUpperCase() + mode.slice(1)}
                    </p>
                    <p className="text-xs text-slate-600">
                      {option
                        ? `${option.departure}–${option.arrival} · ${option.duration}`
                        : `${leg.duration_hours}h transfer${leg.distance_km ? ` · ${leg.distance_km} km` : ""}`}
                      {leg.estimate_only && <Badge variant="outline" className="ml-2">Estimate · not bookable</Badge>}
                    </p>
                    {leg.type === "transport" && option && <p className="text-xs text-slate-600">{displayName(mode, option)} · {option.class} · {option.seats_available} seats left</p>}
                  </div>
                  <p className="text-right text-sm font-semibold text-slate-900 shrink-0">
                    ₹{fmt(leg.type === "transport" && option ? option.price * travelers : leg.group_total)}
                    <span className="block text-[11px] font-normal text-slate-500">{leg.type === "transport" ? "group total" : "estimate"}</span>
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
        {plan.route_duration_minutes != null && (
          <p className="text-sm font-semibold text-slate-700">Door-to-door duration: {Math.floor(plan.route_duration_minutes / 60)}h {plan.route_duration_minutes % 60}m</p>
        )}
        <div className="space-y-2 pt-1">
          <p className="text-sm font-semibold text-slate-800">Available transport options</p>
          {transportOptionGroups.map(({ mode, options }) => {
            const Icon = modeIcon(mode);
            return (
              <section key={mode} className="space-y-2" data-testid={`trip-${mode}-options`}>
                <h5 className="font-semibold text-sm text-slate-800">{modeLabel(mode)}</h5>
                {options.map((option) => {
                  const isSelected = transport?.option?.id === option.id;
                  return (
                    <Card key={option.id} className={`p-3 border ${isSelected ? "border-indigo-500 ring-2 ring-indigo-100" : "border-slate-200"}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-semibold text-sm text-slate-900 flex items-center gap-1.5"><Icon className="w-4 h-4 text-indigo-600" />{displayName(mode, option)}</p>
                          <div className="mt-1 flex gap-1">
                            <Badge variant="outline">{option.tier}</Badge>
                            {option.recommended && <Badge className="bg-indigo-100 text-indigo-800">Recommended</Badge>}
                          </div>
                          <p className="text-xs text-slate-600 mt-1">{option.class} · {option.departure}–{option.arrival} · {option.duration} · {option.seats_available} seats left</p>
                          {option.reason && <p className="text-xs text-indigo-700 mt-1">{option.reason}</p>}
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-bold text-sm">₹{fmt(option.price)} / person</p>
                          <p className="text-xs text-slate-500">Group ₹{fmt(option.price * travelers)}</p>
                          {optionButton("trip_transport", option, mode)}
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </section>
            );
          })}
        </div>
      </section>

      <section className="space-y-3" data-testid="destination-stay">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h4 className="font-heading font-bold text-slate-900">Stay</h4>
            <p className="text-xs text-slate-600">{details.nights} nights · {rooms} room{rooms === 1 ? "" : "s"} · {Math.ceil(travelers / 2)} rooms suggested</p>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-600">
            Rooms
            <Input aria-label="Trip rooms" type="number" min="1" value={rooms} onChange={(event) => onRoomsChange(Math.max(1, Number(event.target.value) || 1))} className="w-16 h-8" />
          </label>
        </div>
        {hotelOptions.map((option) => {
          const isSelected = hotel?.option?.id === option.id;
          return (
            <Card key={option.id} className={`p-3 border ${isSelected ? "border-indigo-500 ring-2 ring-indigo-100" : "border-slate-200"}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-sm text-slate-900 flex items-center gap-1.5"><Hotel className="w-4 h-4 text-indigo-600" />{option.name || option.hotel}</p>
                  <div className="mt-1 flex gap-1">
                    <Badge variant="outline">{option.tier}</Badge>
                    {option.recommended && <Badge className="bg-indigo-100 text-indigo-800">Recommended</Badge>}
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{option.category} · {option.stars} ★ · {option.room_type} · {option.location}</p>
                  {option.reason && <p className="text-xs text-indigo-700 mt-1">{option.reason}</p>}
                </div>
                <div className="text-right shrink-0">
                  <p className="font-bold text-sm">₹{fmt(option.price_per_night)} / night</p>
                  <p className="text-xs text-slate-500">₹{fmt(option.price_per_night * details.nights)} for {details.nights} nights</p>
                  <p className="text-xs text-slate-500">{rooms} room{rooms === 1 ? "" : "s"} · group ₹{fmt(option.price_per_night * details.nights * rooms)}</p>
                  <Button size="sm" variant={isSelected ? "default" : "outline"} onClick={() => onSelectOption("hotel", option, "hotel")}>{isSelected ? "Selected" : "Select"}</Button>
                </div>
              </div>
            </Card>
          );
        })}
      </section>

      <section className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-1" data-testid="destination-cost-breakdown">
        <h4 className="font-heading font-bold text-slate-900 mb-2">Cost breakdown · recommended options</h4>
        {costRows.map(([label, amount]) => (
          <p key={label} className="flex justify-between gap-3 text-sm text-slate-700"><span>{label}</span><span>₹{fmt(amount)}</span></p>
        ))}
        <p className="flex justify-between gap-3 border-t border-slate-200 mt-2 pt-2 font-bold text-slate-900"><span>Grand total</span><span>₹{fmt(grandTotal)}</span></p>
        <p className="text-xs text-slate-600">₹{fmt(plan.per_person)} per person · all prices and travel estimates are simulated.</p>
        {budget > 0 && (
          <div className={`mt-3 rounded-md p-3 text-sm ${plan.budget_status?.over_budget ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-900"}`} data-testid="destination-budget-bar">
            <div className="flex justify-between gap-2"><span>Budget ₹{fmt(budget)}</span><span>Estimate ₹{fmt(grandTotal)}</span></div>
            <div className="h-2 rounded bg-white mt-2 overflow-hidden"><div className={`h-full ${plan.budget_status?.over_budget ? "bg-amber-500" : "bg-emerald-500"}`} style={{ width: `${Math.min(100, (grandTotal / budget) * 100)}%` }} /></div>
            {plan.budget_status?.over_budget
              ? <p className="mt-2">Over budget. Minimum needed: ₹{fmt(minimumNeeded)}. {plan.budget_status.cheaper_changes?.join("; ")}.</p>
              : <p className="mt-2">₹{fmt(budget - grandTotal)} remaining.</p>}
          </div>
        )}
      </section>

      {travelers > 1 && (
        <GroupSplitCard
          title={`${destination} trip`}
          travelers={travelers}
          lines={splitLines}
          rooms={rooms}
          onRoomsChange={onRoomsChange}
          namesText={travelerNames}
          onNamesChange={onNamesChange}
        />
      )}
      {error && <p role="alert" className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}
      {status !== "done" && !checkout && (
        <Button onClick={onOpenCheckout} disabled={loading || status === "processing"} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">
          {loading ? "Preparing review…" : "Book this plan"}
        </Button>
      )}
      {checkout && status !== "done" && (
        <ConfirmationCard
          intent="trip"
          option={checkout.items[0]?.option}
          quantity={travelers}
          nights={details.nights}
          rooms={rooms}
          items={checkout.items}
          preview={checkout.preview}
          user={user}
          initialNames={travelerNames}
          approved={approved}
          requiresApproval
          disabled={loading || status === "failed"}
          onPricingChange={onPricingChange}
          onConfirm={onConfirm}
          onCancel={onCancelCheckout}
        />
      )}
      {bookings.map((booking) => (
        <BookingReceipt key={booking.booking_id} receipt={booking} onNew={onNextBooking} newLabel="Back to plan" />
      ))}
    </Card>
  );
}

export default function ConversationPanel({
  messages,
  user,
  input,
  onInputChange,
  onSend,
  onReset,
  loading,
  speechSupported,
  listening,
  onVoiceInput,
  tripPlan,
  approved = false,
  selections = {},
  onSelectOption,
  selection,
  preview,
  quantity,
  nights,
  rooms = 1,
  onRoomsChange,
  onQuantityChange,
  onNightsChange,
  onConfirm,
  onCancelSelection,
  receipt,
  onNextBooking,
  onEventOptionSelect,
  onBookEventPlan,
  eventBookings = [],
  eventPlanStatus = "idle",
  eventPlanError,
  eventCheckout,
  onOpenEventCheckout,
  onEventPricingChange,
  onCancelEventCheckout,
  onPricingChange,
  onTripOptionSelect,
}) {
  const messagesRef = useRef(null);
  const [travelerNames, setTravelerNames] = useState("");

  useEffect(() => {
    messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setTravelerNames("");
  }, [
    tripPlan?.details?.source,
    tripPlan?.details?.destination,
    tripPlan?.details?.start_date,
    tripPlan?.details?.event,
    tripPlan?.details?.event_city,
    tripPlan?.details?.event_date,
  ]);

  const details = tripPlan?.details || {};
  const selectedTransport = selection && ["flight", "train"].includes(selection.intent)
    ? selections[selection.intent]
    : selections.flight || selections.train;
  const selectedHotel = selections.hotel;
  const totals = selectedTransport || selectedHotel ? {
    transport: selectedTransport ? selectedTransport.option.price * details.travelers : 0,
    hotel: selectedHotel ? selectedHotel.option.price_per_night * details.nights * rooms : 0,
  } : null;
  const estimatedTotal = totals ? totals.transport + totals.hotel : null;
  const minimumTransport = tripPlan?.sections
    ?.filter((tool) => tool === "flight" || tool === "train")
    .flatMap((tool) => tripPlan.options[tool] || [])
    .sort((a, b) => a.price - b.price)[0];
  const minimumHotel = tripPlan?.options?.hotel?.find((option) => option.tier === "Budget");
  const minimumNeeded = (
    (minimumTransport ? minimumTransport.price * details.travelers : 0)
    + (minimumHotel ? minimumHotel.price_per_night * details.nights * rooms : 0)
  ) || null;
  const localTransport = tripPlan?.local_transport?.[0];
  const minimumPlanTotal = minimumNeeded == null
    ? null
    : minimumNeeded + (localTransport ? localTransport.price_per_day * (details.nights + 1) : 0);
  const eventDetails = tripPlan?.kind === "event_travel" ? tripPlan.details : null;
  const eventSelections = tripPlan?.kind === "event_travel" ? selections : {};
  const eventOutbound = eventSelections.outbound;
  const eventReturnOptions = (tripPlan?.options?.return || []).filter(
    (option) => option.intent === (eventOutbound?.intent || tripPlan?.defaults?.outbound?.intent),
  );
  const eventCosts = eventDetails ? {
    tickets: grossEstimate(eventSelections.event.option.price, eventDetails.travelers),
    travel: grossEstimate(eventOutbound.option.price, eventDetails.travelers),
    stay: grossEstimate(eventSelections.hotel.option.price_per_night * rooms),
    local: eventSelections.local.option.price_per_day * tripPlan.local_days,
    return: grossEstimate(eventSelections.return.option.price, eventDetails.travelers),
  } : null;
  const eventTotal = eventCosts ? Object.values(eventCosts).reduce((sum, value) => sum + value, 0) : 0;
  const minOutboundByMode = ["flight", "train", "bus"].map((intent) => {
    const outbound = tripPlan?.options?.outbound?.filter((option) => option.intent === intent) || [];
    const returning = tripPlan?.options?.return?.filter((option) => option.intent === intent) || [];
    return outbound.length && returning.length
      ? {
        intent,
        cost: Math.min(...outbound.map((option) => option.price))
          + Math.min(...returning.map((option) => option.price)),
      }
      : null;
  }).filter((value) => value != null);
  const eventMinimum = tripPlan?.options?.event?.[0]?.price;
  const hotelMinimum = tripPlan?.options?.hotel?.[0]?.price_per_night;
  const localMinimum = Math.min(...(tripPlan?.options?.local || []).map((option) => option.price_per_day));
  const minimumEventTotal = eventMinimum != null && hotelMinimum != null && Number.isFinite(localMinimum) && minOutboundByMode.length
    ? grossEstimate(eventMinimum, eventDetails.travelers)
      + grossEstimate(hotelMinimum)
      + localMinimum * tripPlan.local_days
      + grossEstimate(Math.min(...minOutboundByMode.map((item) => item.cost)), eventDetails.travelers)
    : null;
  const minimumMode = minOutboundByMode.sort((a, b) => a.cost - b.cost)[0]?.intent;
  const selectedNames = eventSelections.outbound && eventSelections.return
    ? `${eventSelections.outbound.intent} (${eventOptionName(eventSelections.outbound.intent, eventSelections.outbound.option)})`
    : "";
  const tripTransport = tripPlan?.sections
    ?.filter((tool) => ["flight", "train"].includes(tool))
    .map((tool) => ({
      ...(selections[tool]?.option
        || tripPlan.options[tool]?.find((option) => option.recommended)
        || tripPlan.options[tool]?.[0]),
      intent: tool,
    }))
    .find(Boolean);
  const tripHotel = selections.hotel?.option
    || tripPlan?.options?.hotel?.find((option) => option.recommended)
    || tripPlan?.options?.hotel?.[0];
  const standaloneLocalOptions = tripPlan?.options?.local_transport || [];
  const standaloneLocalPrice = standaloneLocalOptions.length
    ? Math.min(...standaloneLocalOptions.map((option) => option.price_per_day))
    : 0;
  const standaloneHotelRate = tripPlan?.options?.hotel?.length
    ? Math.min(...tripPlan.options.hotel.map((option) => option.price_per_night))
    : 0;
  const standaloneHotelEstimate = tripPlan?.sections?.includes("hotel")
    ? (selections.hotel?.option || tripHotel)?.price_per_night * details.nights * rooms || 0
    : 0;
  const standaloneLocalEstimate = tripPlan?.sections?.includes("local_transport")
    ? standaloneLocalPrice * (tripPlan.local_transport_days || 0)
    : 0;
  const standaloneEstimatedTotal = standaloneHotelEstimate + standaloneLocalEstimate;
  const standaloneMinimumTotal = (
    (tripPlan?.sections?.includes("hotel") ? standaloneHotelRate * details.nights * rooms : 0)
    + standaloneLocalEstimate
  );
  const tripSplitLines = tripPlan?.kind !== "event_travel" ? [
    ...(tripTransport ? [{
      label: tripTransport.intent === "train" ? "Train travel" : "Flight travel",
      total: grossEstimate(tripTransport.price * details.travelers),
      perPerson: grossEstimate(tripTransport.price),
      shared: false,
    }] : []),
    ...(tripHotel ? [{
      label: "Stay",
      total: grossEstimate(tripHotel.price_per_night * details.nights * rooms),
      perPerson: 0,
      shared: true,
    }] : []),
    ...(localTransport ? [{
      label: "Local transport",
      total: localTransport.price_per_day * (tripPlan.local_transport_days || details.days || details.nights + 1),
      perPerson: 0,
      shared: true,
    }] : []),
  ] : [];
  const eventSplitLines = eventDetails ? [
    {
      label: "Event tickets",
      total: grossEstimate(eventSelections.event.option.price * eventDetails.travelers),
      perPerson: grossEstimate(eventSelections.event.option.price),
      shared: false,
    },
    {
      label: "Outbound travel",
      total: grossEstimate(eventOutbound.option.price * eventDetails.travelers),
      perPerson: grossEstimate(eventOutbound.option.price),
      shared: false,
    },
    {
      label: "Stay",
      total: grossEstimate(eventSelections.hotel.option.price_per_night * rooms),
      perPerson: 0,
      shared: true,
    },
    {
      label: "Local transport",
      total: eventSelections.local.option.price_per_day * tripPlan.local_days,
      perPerson: 0,
      shared: true,
    },
    {
      label: "Return travel",
      total: grossEstimate(eventSelections.return.option.price * eventDetails.travelers),
      perPerson: grossEstimate(eventSelections.return.option.price),
      shared: false,
    },
  ] : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
      <Card className="lg:col-span-5 p-5 bg-white border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-heading text-lg font-bold text-slate-900">Chat with AURA</h3>
            <p className="text-xs text-slate-500">Plan a trip or ask about AURA's travel tools.</p>
          </div>
          <Button variant="outline" size="sm" onClick={onReset} disabled={loading}>New chat</Button>
        </div>
        <div ref={messagesRef} className="h-[360px] overflow-y-auto space-y-3 rounded-lg bg-slate-50 p-3" data-testid="conversation-messages">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500 p-2">Try: “Plan a 3-night trip to Goa from Delhi for two people.”</p>
          )}
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[90%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap ${
                message.role === "user" ? "bg-indigo-600 text-white" : "bg-white border border-slate-200 text-slate-800"
              }`}>
                {message.content}
              </div>
            </div>
          ))}
          {loading && <p className="text-xs text-slate-500 px-2">AURA is thinking…</p>}
        </div>
        <div className="mt-3 flex gap-2">
          <Input
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !loading) {
                event.preventDefault();
                onSend();
              }
            }}
            disabled={loading}
            placeholder="Tell AURA about your trip or ask a question"
            data-testid="conversation-input"
          />
          {speechSupported && (
            <Button type="button" variant="outline" onClick={onVoiceInput} disabled={loading || listening} aria-label={listening ? "Listening" : "Use voice input"}>
              {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </Button>
          )}
          <Button type="button" onClick={() => onSend()} disabled={loading || !input.trim()} className="bg-indigo-600 hover:bg-indigo-700 text-white" aria-label="Send message">
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </Button>
        </div>
        {!speechSupported && <p className="text-[11px] text-slate-500 mt-2">Voice input is not supported in this browser.</p>}
      </Card>

      <div className="lg:col-span-7 space-y-4" data-testid="conversation-results">
        {!tripPlan && (
          <Card className="min-h-40 p-6 bg-white border-dashed border-slate-300 flex items-center justify-center text-center">
            <div>
              <MapPin className="w-5 h-5 text-indigo-500 mx-auto mb-2" />
              <p className="font-medium text-slate-800">Tell AURA where you want to go</p>
              <p className="text-sm text-slate-500 mt-1">Your requested hotel, transport, and trip results will appear here.</p>
            </div>
          </Card>
        )}

        {["destination_trip", "destination_suggestions", "destination_trip_unavailable"].includes(tripPlan?.kind) && (
          <DestinationTripPanel
            plan={tripPlan}
            selections={selections}
            rooms={rooms}
            travelerNames={travelerNames}
            onNamesChange={setTravelerNames}
            onRoomsChange={onRoomsChange}
            onSend={onSend}
            onSelectOption={onTripOptionSelect}
            loading={loading}
            user={user}
            approved={approved}
            checkout={eventCheckout}
            status={eventPlanStatus}
            error={eventPlanError}
            bookings={eventBookings}
            onOpenCheckout={onOpenEventCheckout}
            onPricingChange={onEventPricingChange}
            onConfirm={onBookEventPlan}
            onCancelCheckout={onCancelEventCheckout}
            onNextBooking={onNextBooking}
          />
        )}

        {tripPlan?.kind === "event_travel" && (
          <Card className="p-5 bg-white border-indigo-200 space-y-5" data-testid="event-travel-plan">
            <div className="flex justify-end">
              <PlanPrintAction plan={tripPlan} selections={selections} rooms={rooms} peopleNames={travelerNames} minimumTotal={minimumEventTotal} receipts={[...eventBookings, ...(receipt ? [receipt] : [])]} />
            </div>
            <div>
              <h3 className="font-heading text-lg font-bold text-slate-900">Event + Travel plan</h3>
              <p className="text-sm text-slate-600">
                {eventDetails.source} → {eventDetails.event_city} · {eventDetails.event} · {eventDetails.event_date} · {eventDetails.travelers} traveler{eventDetails.travelers === 1 ? "" : "s"}
              </p>
            </div>
            <ol className="relative space-y-5 border-l-2 border-indigo-100 pl-4">
              <li>
                <p className="font-semibold text-slate-800 mb-2">1. Travel to city · {eventOutbound.option.travel_date}</p>
                <EventOptionGroup
                  part="outbound" title="Choose outbound travel"
                  options={tripPlan.options.outbound}
                  selected={eventOutbound}
                  travelers={eventDetails.travelers}
                  localDays={tripPlan.local_days}
                  tradeoff={tripPlan.tradeoffs?.outbound}
                  onSelect={onEventOptionSelect}
                />
              </li>
              <li>
                <p className="font-semibold text-slate-800 mb-2">2. Hotel · check-in {eventDetails.event_date} · 1 night</p>
                <EventOptionGroup
                  part="hotel" title="Choose a stay"
                  options={tripPlan.options.hotel}
                  selected={eventSelections.hotel}
                  travelers={eventDetails.travelers}
                  localDays={tripPlan.local_days}
                  rooms={rooms}
                  tradeoff={tripPlan.tradeoffs?.hotel}
                  onSelect={onEventOptionSelect}
                />
              </li>
              <li>
                <p className="font-semibold text-slate-800 mb-2">3. Event · {eventDetails.event_date}</p>
                <EventOptionGroup
                  part="event" title="Choose ticket tier"
                  options={tripPlan.options.event}
                  selected={eventSelections.event}
                  travelers={eventDetails.travelers}
                  localDays={tripPlan.local_days}
                  tradeoff={tripPlan.tradeoffs?.event}
                  onSelect={onEventOptionSelect}
                />
              </li>
              <li>
                <p className="font-semibold text-slate-800 mb-2">Local transport · estimated for {tripPlan.local_days} days</p>
                <EventOptionGroup
                  part="local" title="Choose local transport"
                  options={tripPlan.options.local}
                  selected={eventSelections.local}
                  travelers={eventDetails.travelers}
                  localDays={tripPlan.local_days}
                  onSelect={onEventOptionSelect}
                />
              </li>
              <li>
                <p className="font-semibold text-slate-800 mb-2">4. Return · {eventSelections.return.option.travel_date}</p>
                <EventOptionGroup
                  part="return" title={`Choose return travel (${eventOutbound.intent})`}
                  options={eventReturnOptions}
                  selected={eventSelections.return}
                  travelers={eventDetails.travelers}
                  localDays={tripPlan.local_days}
                  tradeoff={tripPlan.tradeoffs?.return?.[eventOutbound.intent]}
                  onSelect={onEventOptionSelect}
                />
              </li>
            </ol>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4" data-testid="event-cost-breakdown">
              <h4 className="font-heading font-bold text-slate-900 mb-2">Cost breakdown</h4>
              {eventCosts && Object.entries({
                "Event tickets": eventCosts.tickets,
                "Outbound travel": eventCosts.travel,
                "Hotel (1 night)": eventCosts.stay,
                "Local transport": eventCosts.local,
                "Return travel": eventCosts.return,
              }).map(([label, amount]) => (
                <p key={label} className="flex justify-between gap-3 text-sm text-slate-700">
                  <span>{label}</span><span>₹{fmt(amount)}</span>
                </p>
              ))}
              <p className="flex justify-between gap-3 border-t border-slate-200 mt-2 pt-2 font-bold text-slate-900">
                <span>Grand total</span><span>₹{fmt(eventTotal)}</span>
              </p>
              <p className="text-[11px] text-slate-500 mt-1">Booking estimates include 18% GST; local transport is an estimate.</p>
              {eventDetails.budget != null && (
                <div className={`mt-3 rounded-md p-3 text-sm ${eventTotal > eventDetails.budget ? "bg-amber-50 text-amber-900" : "bg-emerald-50 text-emerald-900"}`}>
                  Budget ₹{fmt(eventDetails.budget)} · Estimate ₹{fmt(eventTotal)}
                  {eventTotal > eventDetails.budget && (
                    <p className="mt-1">
                      Over budget. Minimum available estimate: ₹{fmt(minimumEventTotal)}.
                      {" "}Cheaper alternative: Budget tickets and stay with the lowest-cost {minimumMode} round trip.
                    </p>
                  )}
                </div>
              )}
            </div>
            {eventDetails.travelers >= 2 && (
              <GroupSplitCard
                title={`${eventDetails.event_city} event trip`}
                travelers={eventDetails.travelers}
                lines={eventSplitLines}
                rooms={rooms}
                onRoomsChange={onRoomsChange}
                namesText={travelerNames}
                onNamesChange={setTravelerNames}
              />
            )}
            {eventPlanError && <p role="alert" className="rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{eventPlanError}</p>}
            {eventPlanStatus !== "done" && !eventCheckout && (
              <Button
                onClick={onOpenEventCheckout}
                disabled={loading || eventPlanStatus === "processing"}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {loading ? "Preparing review…" : "Book this plan"}
              </Button>
            )}
            {eventCheckout && eventPlanStatus !== "done" && (
              <ConfirmationCard
                intent="trip"
                option={eventCheckout.items[0]?.option}
                quantity={eventCheckout.items[0]?.quantity || eventDetails.travelers}
                nights={1}
                rooms={rooms}
                items={eventCheckout.items}
                preview={eventCheckout.preview}
                user={user}
                initialNames={travelerNames}
                approved={approved}
                requiresApproval
                disabled={loading || eventPlanStatus === "failed"}
                onPricingChange={onEventPricingChange}
                onConfirm={onBookEventPlan}
                onCancel={onCancelEventCheckout}
              />
            )}
            {eventBookings.map((booking) => (
              <BookingReceipt key={booking.booking_id} receipt={booking} onNew={onNextBooking} newLabel="Back to plan" />
            ))}
          </Card>
        )}

        {tripPlan?.kind === "tool_results" && (
          <Card className="p-5 bg-white border-indigo-200 space-y-4" data-testid="chat-tool-results">
            <div className="flex justify-end">
              <PlanPrintAction plan={tripPlan} selections={selections} rooms={rooms} peopleNames={travelerNames} receipts={receipt ? [receipt] : []} />
            </div>
            <div>
              <h3 className="font-heading text-lg font-bold text-slate-900">Your results</h3>
              <p className="text-sm text-slate-600">
                {details.city}
                {details.start_date ? ` · ${new Date(`${details.start_date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}` : ""}
                {tripPlan.sections.includes("hotel") ? ` · ${details.nights} nights · ${details.travelers} traveler${details.travelers === 1 ? "" : "s"}` : ""}
                {tripPlan.sections.includes("local_transport") ? ` · ${tripPlan.local_transport_days} days local transport` : ""}
              </p>
            </div>
            {uniqueSections(tripPlan.sections).map((tool) => (
              <section key={tool} className="space-y-2">
                <h4 className="font-heading font-bold text-slate-900">
                  {tool === "hotel" ? "Hotels" : "Local transport"}
                </h4>
                {tripPlan.tradeoffs?.[tool] && <p className="text-xs text-slate-600">{tripPlan.tradeoffs[tool]}</p>}
                {tool === "hotel"
                  ? uniqueById(tripPlan.options.hotel).map((option) => (
                    <OptionCard
                      key={option.id}
                      tool="hotel"
                      option={option}
                      details={details}
                      rooms={rooms}
                      selected={selections.hotel?.option.id === option.id}
                      onSelect={onSelectOption}
                    />
                  ))
                  : uniqueById(tripPlan.options.local_transport).map((option) => (
                    <LocalTransportCard
                      key={option.id}
                      option={option}
                      days={tripPlan.local_transport_days}
                    />
                  ))}
              </section>
            ))}
            {details.budget != null && (
              <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm" data-testid="trip-budget-summary">
                <p className="font-semibold text-slate-900">
                  Estimated {[
                    tripPlan.sections.includes("hotel") ? "stay" : null,
                    tripPlan.sections.includes("local_transport") ? "local transport" : null,
                  ].filter(Boolean).join(" + ")}: ₹{fmt(standaloneEstimatedTotal)} vs budget ₹{fmt(details.budget)}
                </p>
                {standaloneEstimatedTotal > details.budget && (
                  <p className="mt-1 text-amber-800">
                    Over budget. Minimum needed from available options: ₹{fmt(standaloneMinimumTotal)}.
                  </p>
                )}
              </div>
            )}
            {details.travelers >= 2 && (
              <GroupSplitCard
                title={`${details.city} plan`}
                travelers={details.travelers}
                lines={tripSplitLines}
                rooms={rooms}
                onRoomsChange={onRoomsChange}
                namesText={travelerNames}
                onNamesChange={setTravelerNames}
              />
            )}
          </Card>
        )}

        {tripPlan && !["event_travel", "tool_results", "destination_trip", "destination_suggestions", "destination_trip_unavailable"].includes(tripPlan.kind) && (
          <Card className="p-5 bg-white border-indigo-200 space-y-4" data-testid="trip-plan">
            <div className="flex justify-end">
              <PlanPrintAction plan={tripPlan} selections={selections} rooms={rooms} peopleNames={travelerNames} minimumTotal={minimumPlanTotal} receipts={receipt ? [receipt] : []} />
            </div>
            <div>
              <h3 className="font-heading text-lg font-bold text-slate-900">Options for your trip</h3>
              <p className="text-sm text-slate-600">
                {tripPlan.sections.some((tool) => ["flight", "train", "bus"].includes(tool))
                  ? `${details.source} → ${details.destination} · `
                  : `${details.destination} · `}
                {details.start_date} · {details.nights} nights · {details.travelers} traveler{details.travelers === 1 ? "" : "s"}
              </p>
            </div>
            {uniqueSections(tripPlan.sections).map((tool) => {
              const options = uniqueById(tripPlan.options[tool] || []).filter(
                (option) => tool !== "hotel" || !tripPlan.hotel_tier_filter || option.tier === tripPlan.hotel_tier_filter,
              );
              const title = tool === "flight" ? "Flights"
                : tool === "train" ? "Trains"
                  : tool === "bus" ? "Buses"
                    : tool === "local_transport" ? "Local transport"
                      : "Hotels";
              return (
                <section key={tool} className="space-y-2">
                  <h4 className="font-heading font-bold text-slate-900">{title}</h4>
                  {tripPlan.tradeoffs?.[tool] && <p className="text-xs text-slate-600">{tripPlan.tradeoffs[tool]}</p>}
                  {tool === "local_transport" ? uniqueById(tripPlan.options[tool] || []).map((option) => (
                    <LocalTransportCard key={option.id} option={option} days={details.days || details.nights + 1} />
                  )) : options.map((option) => (
                    <OptionCard
                      key={option.id}
                      tool={tool}
                      option={option}
                      details={details}
                      rooms={rooms}
                      selected={selections[tool]?.option.id === option.id}
                      onSelect={onSelectOption}
                    />
                  ))}
                </section>
              );
            })}
            {details.budget != null && (
              <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-sm" data-testid="trip-budget-summary">
                {totals ? (
                  <>
                    <p className="font-semibold text-slate-900">Selected transport + hotel: ₹{fmt(estimatedTotal)} vs budget ₹{fmt(details.budget)}</p>
                    {estimatedTotal > details.budget && (
                      <p className="mt-1 text-amber-800">
                        Over budget. Minimum needed from available options: ₹{fmt(minimumNeeded)}.
                        {" "}Try Budget tier options to reduce the estimate.
                      </p>
                    )}
                  </>
                ) : <p>Select a transport and hotel to compare the total with your budget.</p>}
              </div>
            )}
            {details.travelers >= 2 && (
              <GroupSplitCard
                title={`${details.destination} trip`}
                travelers={details.travelers}
                lines={tripSplitLines}
                rooms={rooms}
                onRoomsChange={onRoomsChange}
                namesText={travelerNames}
                onNamesChange={setTravelerNames}
              />
            )}
            {(localTransport || tripPlan.itinerary?.length > 0) && (
              <div className="rounded-lg bg-slate-50 p-3 text-sm space-y-2">
                {localTransport && (
                  <p className="text-slate-700">
                    Estimated local transport: ₹{fmt(localTransport.price_per_day)} / day ·
                    {" "}₹{fmt(localTransport.price_per_day * (details.nights + 1))} for {details.nights + 1} days
                  </p>
                )}
                {tripPlan.itinerary?.length > 0 && (
                  <div>
                    <p className="font-semibold text-slate-800">Day-by-day itinerary</p>
                    <ol className="mt-1 space-y-1 text-slate-600">
                      {tripPlan.itinerary.map((day) => (
                        <li key={`${day.day}-${day.date}`}>Day {day.day} · {day.date}: {day.activity}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )}
          </Card>
        )}

        {selection && preview && !receipt && (
          <ConfirmationCard
            intent={selection.intent}
            option={selection.option}
            quantity={quantity}
            nights={nights}
            rooms={rooms}
            onRoomsChange={onRoomsChange}
            preview={preview}
            user={user}
            initialNames={travelerNames}
            approved={approved}
            requiresApproval
            disabled={loading}
            onQuantityChange={onQuantityChange}
            onNightsChange={onNightsChange}
            onPricingChange={onPricingChange}
            onConfirm={onConfirm}
            onCancel={onCancelSelection}
          />
        )}
        {receipt && <BookingReceipt receipt={receipt} onNew={onNextBooking} newLabel="Choose next option" />}
      </div>
    </div>
  );
}
