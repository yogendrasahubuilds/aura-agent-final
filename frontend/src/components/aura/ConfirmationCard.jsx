import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CheckCircle2, X } from "lucide-react";

const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);

const QTY_LABEL = { movie: "Tickets", flight: "Passengers", hotel: "Guests" };

export default function ConfirmationCard({ intent, option, quantity, nights, preview, seats = [], onQuantityChange, onNightsChange, onConfirm, onCancel }) {
  const amount = preview?.amount || { subtotal: 0, tax: 0, total: 0 };
  const title = intent === "movie" ? option.cinema : intent === "hotel" ? option.hotel : `${option.airline} ${option.flight_no}`;

  return (
    <Card className="p-5 bg-indigo-50/50 border-indigo-200" data-testid="confirmation-card">
      <h3 className="font-heading font-bold text-slate-900 mb-3">Review & Confirm</h3>
      <div className="space-y-1 text-sm text-slate-700">
        <p><span className="text-slate-500">Selection:</span> <span className="font-semibold">{title}</span></p>
        {intent === "movie" && <p><span className="text-slate-500">Show:</span> {option.movie} · {option.time}</p>}
        {intent === "movie" && seats.length > 0 && (
          <p><span className="text-slate-500">Seats:</span> <span className="font-mono font-semibold">{seats.join(", ")}</span></p>
        )}
        {intent === "flight" && <p><span className="text-slate-500">Route:</span> {option.source} → {option.destination} · {option.departure}</p>}
        {intent === "hotel" && <p><span className="text-slate-500">Room:</span> {option.room_type}</p>}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <div>
          <Label className="text-xs text-slate-600">{QTY_LABEL[intent]}</Label>
          <Input
            type="number"
            min={1}
            value={quantity}
            onChange={(e) => onQuantityChange(parseInt(e.target.value) || 1)}
            className="h-10 mt-1"
            data-testid="quantity-input"
          />
        </div>
        {intent === "hotel" && (
          <div>
            <Label className="text-xs text-slate-600">Nights</Label>
            <Input
              type="number"
              min={1}
              value={nights}
              onChange={(e) => onNightsChange(parseInt(e.target.value) || 1)}
              className="h-10 mt-1"
              data-testid="nights-input"
            />
          </div>
        )}
      </div>

      <div className="mt-5 bg-white rounded-lg border border-indigo-200 p-4 space-y-1.5 text-sm">
        <div className="flex justify-between text-slate-600">
          <span>Subtotal</span><span>₹{fmt(amount.subtotal)}</span>
        </div>
        <div className="flex justify-between text-slate-600">
          <span>GST (18%)</span><span>₹{fmt(amount.tax)}</span>
        </div>
        <div className="flex justify-between font-heading font-extrabold text-slate-900 text-base pt-2 border-t border-slate-200">
          <span>Total</span><span data-testid="total-amount">₹{fmt(amount.total)}</span>
        </div>
      </div>

      <div className="flex gap-2 mt-5">
        <Button onClick={onConfirm} className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="confirm-booking-btn">
          <CheckCircle2 className="w-4 h-4 mr-1.5" /> Confirm & Create Mock Booking
        </Button>
        <Button variant="outline" onClick={onCancel} data-testid="cancel-booking-btn">
          <X className="w-4 h-4 mr-1.5" />Cancel
        </Button>
      </div>
      <p className="text-[11px] text-slate-500 mt-3">
        Note: This is a simulated booking. No payment or real reservation is made.
      </p>
    </Card>
  );
}
