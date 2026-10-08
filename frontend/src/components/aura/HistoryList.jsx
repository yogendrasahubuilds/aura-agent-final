import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Film, Hotel, Plane } from "lucide-react";

const ICON = { movie: Film, hotel: Hotel, flight: Plane };
const COLOR = {
  movie: "bg-rose-50 text-rose-700 border-rose-200",
  hotel: "bg-emerald-50 text-emerald-700 border-emerald-200",
  flight: "bg-blue-50 text-blue-700 border-blue-200",
};
const fmt = (n) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(n);

export default function HistoryList({ bookings, onRefresh }) {
  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-heading text-2xl font-bold text-slate-900">Past Simulated Bookings</h2>
        <Button variant="outline" size="sm" onClick={onRefresh} data-testid="refresh-history-btn">
          <RefreshCw className="w-4 h-4 mr-1.5" />Refresh
        </Button>
      </div>
      {!bookings?.length ? (
        <Card className="p-10 bg-white border-dashed text-center text-sm text-slate-500">
          No bookings yet. Try a quick demo on the Agent tab.
        </Card>
      ) : (
        <div className="space-y-3">
          {bookings.map((b) => {
            const Icon = ICON[b.intent] || Film;
            const title = b.intent === "movie" ? b.option?.cinema : b.intent === "hotel" ? b.option?.hotel : `${b.option?.airline} ${b.option?.flight_no}`;
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
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </section>
  );
}
