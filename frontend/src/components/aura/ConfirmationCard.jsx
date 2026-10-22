import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CheckCircle2, CreditCard, X } from "lucide-react";

const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(n) || 0);
const QTY_LABEL = {
  movie: "Ticket holder",
  flight: "Passenger",
  train: "Passenger",
  bus: "Passenger",
  cricket: "Ticket holder",
  concert: "Ticket holder",
  hotel: "Guest",
};
const isTransport = (intent) => ["flight", "train", "bus"].includes(intent);

function initialPassenger(user, index, names = []) {
  return { name: names[index] || (index === 0 ? user?.name || "" : ""), age: "", gender: "" };
}

export default function ConfirmationCard({
  intent,
  option,
  quantity,
  nights,
  rooms = 1,
  preview,
  items = [],
  seats = [],
  user,
  initialNames = "",
  approved = true,
  requiresApproval = false,
  onQuantityChange,
  onNightsChange,
  onRoomsChange,
  onPricingChange,
  onConfirm,
  onCancel,
  confirmLabel,
  disabled = false,
}) {
  const passengerNames = useMemo(() => initialNames.split(",").map((name) => name.trim()), [initialNames]);
  const [passengers, setPassengers] = useState(() => Array.from({ length: quantity }, (_, index) => initialPassenger(user, index, passengerNames)));
  const [email, setEmail] = useState(user?.email || "");
  const [phone, setPhone] = useState("");
  const [promo, setPromo] = useState("");
  const [insurance, setInsurance] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("UPI");
  const [fakePaymentValue, setFakePaymentValue] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    setPassengers((current) => Array.from({ length: quantity }, (_, index) => current[index] || initialPassenger(user, index, passengerNames)));
  }, [quantity, user, initialNames, passengerNames]);

  const bookingItems = useMemo(() => items.length ? items : [{
    intent,
    option,
    quantity,
    nights,
    rooms,
    preview,
  }], [items, intent, option, quantity, nights, rooms, preview]);
  const firstItem = bookingItems[0] || {};
  const hasMultiItems = items.length > 1;
  const amount = useMemo(() => {
    if (hasMultiItems && preview?.amount) return preview.amount;
    const amounts = bookingItems.map((item) => item.preview?.amount).filter(Boolean);
    if (!amounts.length) return preview?.amount || {};
    if (amounts.length === 1) return amounts[0];
    return {
      subtotal: amounts.reduce((sum, row) => sum + (row.subtotal || 0), 0),
      fees: amounts.reduce((sum, row) => sum + (row.fees || 0), 0),
      discount: amounts.reduce((sum, row) => sum + (row.discount || 0), 0),
      tax: amounts.reduce((sum, row) => sum + (row.tax || 0), 0),
      total: amounts.reduce((sum, row) => sum + (row.total || 0), 0),
      per_person: amounts.reduce((sum, row) => sum + (row.per_person || 0), 0),
      breakdown: bookingItems.flatMap((item) => (item.preview?.amount?.breakdown || []).map((line) => ({
        ...line,
        label: bookingItems.length > 1 ? `${item.label || item.intent}: ${line.label}` : line.label,
      }))),
      promo_valid: amounts.every((row) => row.promo_valid !== false),
      promo_code: amounts.find((row) => row.promo_code)?.promo_code,
      gst_rate: amounts.length === 1 ? amounts[0].gst_rate : null,
    };
  }, [bookingItems, hasMultiItems, preview]);
  const isTransportBooking = bookingItems.some((item) => isTransport(item.intent));
  const title = firstItem.intent === "movie"
    ? firstItem.option?.cinema
    : firstItem.intent === "hotel"
      ? firstItem.option?.hotel
      : firstItem.intent === "flight"
        ? `${firstItem.option?.airline || "Flight"} ${firstItem.option?.flight_no || ""}`.trim()
        : firstItem.option?.train_name || firstItem.option?.operator || firstItem.option?.match || firstItem.option?.event;

  const updatePassenger = (index, field, value) => setPassengers((current) => current.map((person, personIndex) => (
    personIndex === index ? { ...person, [field]: value } : person
  )));
  const applyPricing = () => onPricingChange?.(promo, insurance);
  const submit = async (event) => {
    event.preventDefault();
    if (!approved && requiresApproval) {
      await onConfirm({ passengers, contact: { email, phone }, promo_code: promo || null, insurance, payment_method: paymentMethod });
      return;
    }
    setProcessing(true);
    await new Promise((resolve) => setTimeout(resolve, 2000));
    try {
      await onConfirm({
        passengers: passengers.map((person) => ({ ...person, age: Number(person.age) })),
        contact: { email, phone },
        promo_code: promo || null,
        insurance,
        payment_method: paymentMethod,
        seats,
      });
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Card className="p-5 bg-indigo-50/50 border-indigo-200" data-testid="confirmation-card">
      <h3 className="font-heading font-bold text-slate-900 mb-3">Review &amp; Confirm</h3>
      <div className="space-y-1 text-sm text-slate-700">
        <p><span className="text-slate-500">Selection:</span> <span className="font-semibold">{title}</span></p>
        {["flight", "train", "bus"].includes(firstItem.intent) && (
          <p><span className="text-slate-500">Route &amp; time:</span> {firstItem.option?.source} → {firstItem.option?.destination} · {firstItem.option?.departure}–{firstItem.option?.arrival} · {firstItem.option?.class}</p>
        )}
        {firstItem.intent === "hotel" && <p><span className="text-slate-500">Stay:</span> {firstItem.option?.room_type} · {nights} night(s) · {rooms} room(s)</p>}
        {["cricket", "concert"].includes(firstItem.intent) && <p><span className="text-slate-500">Venue:</span> {firstItem.option?.stadium || firstItem.option?.venue} · {firstItem.option?.city} · {firstItem.option?.date}</p>}
        {firstItem.intent === "movie" && <p><span className="text-slate-500">Show:</span> {firstItem.option?.movie} · {firstItem.option?.time}{seats.length ? ` · Seats ${seats.join(", ")}` : ""}</p>}
        {bookingItems.length > 1 && (
          <ul className="mt-2 list-disc pl-5">{bookingItems.map((item) => <li key={`${item.intent}-${item.option?.id}`}>{item.label || item.intent}: {item.option?.hotel || item.option?.airline || item.option?.train_name || item.option?.operator || item.option?.match || item.option?.event}</li>)}</ul>
        )}
      </div>

      <form onSubmit={submit} className="space-y-5">
        {!items.length && (
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div><Label htmlFor="booking-quantity">Travelers / tickets</Label><Input id="booking-quantity" type="number" min={1} value={quantity} onChange={(event) => onQuantityChange?.(Math.max(1, Number(event.target.value) || 1))} className="mt-1" /></div>
            {intent === "hotel" && <div><Label htmlFor="booking-nights">Nights</Label><Input id="booking-nights" type="number" min={1} value={nights} onChange={(event) => onNightsChange?.(Math.max(1, Number(event.target.value) || 1))} className="mt-1" /></div>}
            {intent === "hotel" && onRoomsChange && <div><Label htmlFor="booking-rooms">Rooms</Label><Input id="booking-rooms" type="number" min={1} value={rooms} onChange={(event) => onRoomsChange(Math.max(1, Number(event.target.value) || 1))} className="mt-1" /></div>}
          </div>
        )}
        <section className="mt-5 rounded-lg border border-indigo-200 bg-white p-4">
          <h4 className="font-semibold text-slate-900">Traveler details</h4>
          <div className="mt-3 space-y-3">
            {passengers.map((person, index) => (
              <div key={index} className="grid grid-cols-1 gap-2 rounded-md border border-slate-100 p-3 sm:grid-cols-[1.5fr_0.6fr_1fr]">
                <div><Label>{QTY_LABEL[intent] || "Traveler"} {index + 1} · Full name</Label><Input required autoComplete={index === 0 ? "name" : "off"} value={person.name} onChange={(event) => updatePassenger(index, "name", event.target.value)} className="mt-1" /></div>
                <div><Label htmlFor={`traveler-age-${index}`}>Age</Label><Input id={`traveler-age-${index}`} type="number" min="0" max="120" required value={person.age} onChange={(event) => updatePassenger(index, "age", event.target.value)} className="mt-1" /></div>
                <div><Label htmlFor={`traveler-gender-${index}`}>Gender</Label><select id={`traveler-gender-${index}`} required value={person.gender} onChange={(event) => updatePassenger(index, "gender", event.target.value)} className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"><option value="">Select</option><option>Female</option><option>Male</option><option>Non-binary</option><option>Prefer not to say</option></select></div>
              </div>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div><Label htmlFor="booking-contact-email">Contact email</Label><Input id="booking-contact-email" type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1" /></div>
            <div><Label htmlFor="booking-contact-phone">Contact phone</Label><Input id="booking-contact-phone" type="tel" required minLength={10} maxLength={15} autoComplete="tel" value={phone} onChange={(event) => setPhone(event.target.value)} className="mt-1" /></div>
          </div>
        </section>

        <section className="rounded-lg border border-indigo-200 bg-white p-4">
          <h4 className="mb-2 font-semibold text-slate-900">Fare breakdown</h4>
          <div className="max-h-48 space-y-1 overflow-y-auto text-sm">
            {(amount.breakdown || []).map((line, index) => <p key={`${line.label}-${index}`} className="flex justify-between gap-3 text-slate-600"><span>{line.label}</span><span>₹{fmt(line.amount)}</span></p>)}
          </div>
          <div className="mt-2 space-y-1 border-t border-slate-200 pt-2 text-sm">
            <p className="flex justify-between"><span>Subtotal</span><span>₹{fmt(amount.subtotal)}</span></p>
            <p className="flex justify-between"><span>Taxes and fees</span><span>₹{fmt(amount.fees)}</span></p>
            <p className="flex justify-between"><span>Discount</span><span>−₹{fmt(amount.discount)}</span></p>
            <p className="flex justify-between"><span>{amount.gst_rate == null ? "GST (rates shown above)" : `GST (${amount.gst_rate}%)`}</span><span>₹{fmt(amount.tax)}</span></p>
            <p className="flex justify-between border-t border-slate-200 pt-2 font-heading text-base font-extrabold text-slate-900"><span>Grand total</span><span data-testid="total-amount">₹{fmt(amount.total)}</span></p>
            {quantity > 1 && <p className="flex justify-between font-semibold text-indigo-700"><span>Per person</span><span>₹{fmt(amount.per_person ?? amount.total / quantity)}</span></p>}
          </div>
        </section>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto]">
          <div className="flex gap-2">
            <Input aria-label="Promo code" value={promo} onChange={(event) => setPromo(event.target.value.toUpperCase())} placeholder="Promo code (AURA100, WELCOME10)" />
            <Button type="button" variant="outline" onClick={applyPricing}>Apply</Button>
          </div>
          {promo && amount.promo_valid === false && <p role="alert" className="text-sm text-rose-700 sm:col-span-2">Invalid code</p>}
        </div>
        {isTransportBooking && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={insurance} onChange={(event) => { setInsurance(event.target.checked); onPricingChange?.(promo, event.target.checked); }} />
            Add simulated travel insurance
          </label>
        )}

        <section className="rounded-lg border border-indigo-200 bg-white p-4">
          <h4 className="font-semibold text-slate-900">Simulated payment</h4>
          <div className="mt-2 flex flex-wrap gap-4 text-sm">
            {["UPI", "Card", "Net Banking"].map((method) => <label key={method} className="flex items-center gap-2"><input type="radio" name="payment-method" value={method} checked={paymentMethod === method} onChange={() => setPaymentMethod(method)} />{method}</label>)}
          </div>
          {paymentMethod !== "Net Banking" && <Input aria-label={paymentMethod === "UPI" ? "Demo UPI handle" : "Demo card details"} autoComplete="off" value={fakePaymentValue} onChange={(event) => setFakePaymentValue(event.target.value)} placeholder={paymentMethod === "UPI" ? "Demo UPI handle (not saved)" : "Demo card number (not saved)"} className="mt-3" />}
          <p className="mt-2 text-xs font-medium text-amber-800">Simulated payment, no money is charged. Demo payment details are never sent or stored.</p>
        </section>

        <div className="flex gap-2">
          <Button type="submit" disabled={processing || disabled || !amount.total} className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700" data-testid="confirm-booking-btn">
            {processing ? "Processing payment..." : requiresApproval && !approved ? "Approve & Run" : confirmLabel || <><CreditCard className="mr-1.5 h-4 w-4" />Pay ₹{fmt(amount.total)} &amp; Confirm</>}
          </Button>
          <Button type="button" variant="outline" onClick={onCancel} data-testid="cancel-booking-btn"><X className="mr-1.5 h-4 w-4" />Cancel</Button>
        </div>
      </form>
    </Card>
  );
}
