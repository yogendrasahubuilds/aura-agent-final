import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Film, Hotel, Plane, Train, Bus, Music, Trophy } from "lucide-react";
import BookingReceipt from "@/components/aura/BookingReceipt";

const ICON = {
  movie: Film,
  hotel: Hotel,
  flight: Plane,
  train: Train,
  bus: Bus,
  cricket: Trophy,
  concert: Music,
};
const COLOR = {
  movie: "bg-rose-50 text-rose-700 border-rose-200",
  hotel: "bg-emerald-50 text-emerald-700 border-emerald-200",
  flight: "bg-blue-50 text-blue-700 border-blue-200",
  train: "bg-blue-50 text-blue-700 border-blue-200",
  bus: "bg-blue-50 text-blue-700 border-blue-200",
  cricket: "bg-amber-50 text-amber-700 border-amber-200",
  concert: "bg-purple-50 text-purple-700 border-purple-200",
};
const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);

export default function HistoryList({ bookings = [], runs = [], onRefresh }) {
  const [selectedBooking, setSelectedBooking] = useState(null);
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-heading text-2xl font-bold text-slate-900">Past Simulated Bookings</h2>
        <Button variant="outline" size="sm" onClick={onRefresh} data-testid="refresh-history-btn">
          <RefreshCw className="w-4 h-4 mr-1.5" />Refresh
        </Button>
      </div>
      {!bookings.length && !runs.length ? (
        <Card className="p-10 bg-white border-dashed text-center text-sm text-slate-500">
          No agent runs yet. Try a request on the Agent tab.
        </Card>
      ) : (
        <div className="space-y-3">
          {runs.map((run) => (
            <Card key={run.run_id} className="p-4 bg-white border-slate-200">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-slate-900">{run.request}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(run.created_at).toLocaleString("en-IN")}
                  </p>
                  <ol className="mt-3 space-y-1">
                    {(run.steps || []).map((step, index) => (
                      <li key={`${run.run_id}-${index}`} className="text-xs text-slate-600">
                        {index + 1}. {step.tool} — {step.status}
                      </li>
                    ))}
                  </ol>
                </div>
                <Badge variant="outline" className="capitalize shrink-0">{run.status}</Badge>
              </div>
            </Card>
          ))}
          {bookings.map((b) => {
            const Icon = ICON[b.intent] || Film;
            const title = b.intent === "movie"
              ? b.option?.cinema
              : b.intent === "hotel"
                ? b.option?.hotel
                : b.intent === "flight"
                  ? `${b.option?.airline} ${b.option?.flight_no}`
                  : b.option?.train_name || b.option?.operator || b.option?.match || b.option?.event;
            return (
              <Card key={b.booking_id} className="p-4 bg-white border-slate-200 hover:border-indigo-400 transition-colors">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${COLOR[b.intent]}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-mono font-bold text-slate-900 text-sm">{b.booking_id}</p>
                      <p className="text-xs text-slate-500">{title}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="font-heading font-bold text-slate-900">₹{fmt(b.amount?.total || 0)}</p>
                      <p className="text-[10px] text-slate-400">{new Date(b.created_at).toLocaleString("en-IN")}</p>
                    </div>
                    <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 border">
                      {b.status}
                    </Badge>
                    <Button variant="outline" size="sm" onClick={() => setSelectedBooking(b)}>
                      View e-ticket
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
          {selectedBooking && (
            <BookingReceipt
              receipt={selectedBooking}
              onNew={() => setSelectedBooking(null)}
              newLabel="Back to history"
            />
          )}
        </div>
      )}
    </section>
  );
}
