import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Download, ArrowLeft } from "lucide-react";
import { downloadBookingPdf } from "@/lib/pdf";
import { makeBookingQr } from "@/lib/qr";

const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(Number(n) || 0);

function bookingTitle(intent, option = {}) {
  if (intent === "movie") return `${option.movie || ""} · ${option.cinema || ""}`;
  if (intent === "hotel") return option.hotel || "Hotel booking";
  if (intent === "flight") return `${option.airline || "Flight"} ${option.flight_no || ""}`.trim();
  return option.train_name || option.operator || option.match || option.event || "Booking";
}

export default function BookingReceipt({
  receipt,
  onNew,
  newLabel = "Back to plan",
  showActions = true,
}) {
  const {
    booking_id, intent, option = {}, quantity = 1, amount = {}, status, extra = {},
    seats = [], passengers = [], pnr, transaction_id: transactionId, payment_timestamp: paymentTimestamp,
    payment_method: paymentMethod, fare_breakdown: fareBreakdown = amount.breakdown || [], contact = {},
  } = receipt;
  const title = bookingTitle(intent, option);
  const qr = makeBookingQr(booking_id);

  return (
    <Card className="overflow-hidden border border-emerald-300 bg-white shadow-lg" data-testid="booking-receipt">
      <div className="bg-gradient-to-r from-indigo-950 via-indigo-700 to-cyan-700 p-5 text-white">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-8 w-8 text-emerald-300" />
            <div><p className="text-xs uppercase tracking-[.18em] text-indigo-100">AURA e-ticket</p><h3 className="font-heading text-2xl font-extrabold">Booking Confirmed</h3></div>
          </div>
          <Badge className="border border-white/30 bg-white/15 text-white">{status || "confirmed"}</Badge>
        </div>
      </div>
      <div className="grid gap-5 p-5 lg:grid-cols-[1fr_auto]">
        <div className="min-w-0 space-y-5">
          <section className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Booking ID</p><p className="font-mono text-lg font-bold text-slate-900">{booking_id}</p></div>
            {pnr && <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">PNR</p><p className="font-mono text-lg font-bold text-slate-900">{pnr}</p></div>}
            <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Transaction ID</p><p className="font-mono font-semibold text-slate-900">{transactionId || "Not available"}</p></div>
            <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Booked</p><p className="font-medium text-slate-900">{paymentTimestamp ? new Date(paymentTimestamp).toLocaleString("en-IN") : new Date(receipt.created_at).toLocaleString("en-IN")}</p></div>
            {contact.email && <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Contact email</p><p className="font-medium text-slate-900">{contact.email}</p></div>}
            {contact.phone && <div className="rounded-lg bg-slate-50 p-3"><p className="text-xs text-slate-500">Contact phone</p><p className="font-medium text-slate-900">{contact.phone}</p></div>}
          </section>

          <section className="rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50 to-cyan-50 p-4">
            <p className="text-xs uppercase tracking-wide text-indigo-600">{intent}</p>
            <h4 className="font-heading text-lg font-bold text-slate-900">{title}</h4>
            {["flight", "train", "bus"].includes(intent) && <p className="mt-1 text-sm text-slate-700">{option.source} → {option.destination} · {option.departure}–{option.arrival} · {option.duration} · {option.class}</p>}
            {intent === "hotel" && <p className="mt-1 text-sm text-slate-700">{option.location} · {option.room_type} · {extra.nights || 1} night(s) · {extra.rooms || 1} room(s)</p>}
            {["cricket", "concert"].includes(intent) && <p className="mt-1 text-sm text-slate-700">{option.stadium || option.venue} · {option.city} · {option.date} · {option.departure}–{option.arrival} · {option.class}</p>}
            {intent === "movie" && <p className="mt-1 text-sm text-slate-700">{option.time} · {option.screen}{seats.length ? ` · Seats ${seats.join(", ")}` : ""}</p>}
            <p className="mt-2 text-xs text-slate-500">{quantity} traveler(s){paymentMethod ? ` · ${paymentMethod} (simulated)` : ""}</p>
          </section>

          <section>
            <h4 className="mb-2 font-semibold text-slate-900">Passenger / guest details</h4>
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-2">Name</th><th className="px-3 py-2">Age</th><th className="px-3 py-2">Gender</th></tr></thead>
                <tbody>{passengers.map((person, index) => <tr key={`${person.name}-${index}`} className="border-t border-slate-100"><td className="px-3 py-2 font-medium">{person.name}</td><td className="px-3 py-2">{person.age}</td><td className="px-3 py-2">{person.gender}</td></tr>)}</tbody>
              </table>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 p-4">
            <h4 className="mb-2 font-semibold text-slate-900">Fare breakdown</h4>
            <div className="space-y-1 text-sm">{fareBreakdown.map((line, index) => <p key={`${line.label}-${index}`} className="flex justify-between gap-3 text-slate-600"><span>{line.label}</span><span>₹{fmt(line.amount)}</span></p>)}</div>
            <div className="mt-2 flex justify-between border-t border-slate-200 pt-2 font-heading text-lg font-extrabold text-slate-900"><span>Grand total</span><span>₹{fmt(amount.total)}</span></div>
            {quantity > 1 && <p className="mt-1 text-right text-sm font-semibold text-indigo-700">Per person: ₹{fmt(amount.per_person ?? amount.total / quantity)}</p>}
          </section>
          <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-900"><strong>Cancellation policy:</strong> {receipt.cancellation_policy || "Simulated bookings cannot be cancelled or exchanged."}</div>
          <p className="text-xs font-medium text-slate-500">Simulated booking, no real reservation. Simulated payment only; no money was charged.</p>
        </div>
        <div className="flex flex-col items-center gap-2 self-start rounded-lg border border-slate-200 bg-white p-3">
          <svg viewBox="0 0 21 21" role="img" aria-label={`QR code for booking ${booking_id}`} className="h-32 w-32">
            <rect width="21" height="21" fill="white" />
            {qr.flatMap((row, y) => row.map((enabled, x) => enabled && <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" fill="#172554" />))}
          </svg>
          <span className="text-[10px] font-medium text-slate-500">BOOKING ID QR</span>
        </div>
      </div>
      {showActions && (
        <div className="flex flex-wrap gap-2 border-t border-slate-100 bg-slate-50 p-4">
          <Button onClick={() => downloadBookingPdf(receipt)} className="bg-indigo-600 text-white hover:bg-indigo-700" data-testid="download-ticket-btn">
            <Download className="mr-1.5 h-4 w-4" />Download e-ticket (PDF)
          </Button>
          {onNew && <Button variant="outline" onClick={onNew} data-testid="new-booking-btn"><ArrowLeft className="mr-1.5 h-4 w-4" />{newLabel}</Button>}
        </div>
      )}
    </Card>
  );
}
