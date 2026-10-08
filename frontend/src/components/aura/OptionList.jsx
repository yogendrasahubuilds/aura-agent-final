import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MapPin, Users, Star, Plane, ArrowRight, TrendingDown, Flame, Store } from "lucide-react";

const fmt = (n) => new Intl.NumberFormat("en-IN").format(n);

function PriceBadges({ opt }) {
  return (
    <div className="flex flex-wrap gap-1 justify-end">
      {opt.is_cheapest && (
        <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 border text-[10px]">
          <Flame className="w-3 h-3 mr-0.5" />Cheapest
        </Badge>
      )}
      {!opt.is_cheapest && opt.save_pct_vs_max >= 10 && (
        <Badge className="bg-sky-100 text-sky-800 border-sky-300 border text-[10px]">
          <TrendingDown className="w-3 h-3 mr-0.5" />Save {opt.save_pct_vs_max}%
        </Badge>
      )}
      {opt.is_premium && (
        <Badge className="bg-amber-100 text-amber-800 border-amber-300 border text-[10px]">Premium</Badge>
      )}
    </div>
  );
}

function Provider({ opt }) {
  if (!opt.provider) return null;
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 mt-1">
      <Store className="w-3 h-3" />via {opt.provider}
    </span>
  );
}

export default function OptionList({ intent, options, selectedId, onSelect }) {
  if (!options?.length) {
    return (
      <Card className="p-5 bg-white border-slate-200 text-sm text-slate-500">
        No options found. Try changing the city or date.
      </Card>
    );
  }
  const prices = options.map((o) => intent === "hotel" ? o.price_per_night : o.price).filter(Boolean);
  const min = Math.min(...prices);
  const max = Math.max(...prices);

  return (
    <div className="space-y-3" data-testid="option-list">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-heading font-bold text-slate-900">Compared Options ({options.length})</h3>
        {max > min && (
          <p className="text-xs text-slate-500">
            Prices range from <span className="font-semibold text-emerald-700">₹{fmt(min)}</span> to <span className="font-semibold">₹{fmt(max)}</span> · sorted cheapest first
          </p>
        )}
      </div>
      {options.map((o) => {
        const isSelected = o.id === selectedId;
        return (
          <Card
            key={o.id}
            className={`p-4 bg-white transition-all cursor-pointer border ${
              isSelected ? "border-indigo-500 ring-2 ring-indigo-200" : o.is_cheapest ? "border-emerald-300" : "border-slate-200 hover:border-indigo-400"
            }`}
            onClick={() => onSelect(o)}
            data-testid={`option-${o.id}`}
          >
            {intent === "movie" && (
              <div className="flex flex-col sm:flex-row justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-heading font-bold text-slate-900">{o.cinema}</h4>
                    <Badge variant="outline" className="text-[10px]">{o.format}</Badge>
                  </div>
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-1"><MapPin className="w-3 h-3" />{o.location}</p>
                  <p className="text-sm text-slate-700 mt-2">
                    <span className="font-semibold text-rose-600">{o.movie}</span> · {o.time} · {o.screen}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">{o.seats_available} seats available</p>
                  <Provider opt={o} />
                </div>
                <div className="text-right flex sm:flex-col items-end justify-between sm:min-w-[120px]">
                  <div>
                    <PriceBadges opt={o} />
                    <p className="font-heading font-extrabold text-xl text-slate-900 mt-1">₹{fmt(o.price)}</p>
                    <p className="text-[11px] text-slate-500">per ticket</p>
                  </div>
                  <Button size="sm" variant={isSelected ? "default" : "outline"} data-testid={`select-${o.id}`}>
                    {isSelected ? "Selected" : "Select"}
                  </Button>
                </div>
              </div>
            )}

            {intent === "hotel" && (
              <div className="flex flex-col sm:flex-row justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="font-heading font-bold text-slate-900">{o.hotel}</h4>
                    <Badge variant="outline" className="text-[10px] bg-amber-50 border-amber-200 text-amber-800">
                      <Star className="w-3 h-3 mr-0.5 fill-amber-500 text-amber-500" /> {o.rating}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-1"><MapPin className="w-3 h-3" />{o.location}</p>
                  <p className="text-sm text-slate-700 mt-2">{o.room_type}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {o.amenities?.map((a, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600">{a}</span>
                    ))}
                  </div>
                  <p className="text-xs text-slate-500 mt-2">{o.rooms_available} rooms available</p>
                  <Provider opt={o} />
                </div>
                <div className="text-right flex sm:flex-col items-end justify-between sm:min-w-[120px]">
                  <div>
                    <PriceBadges opt={o} />
                    <p className="font-heading font-extrabold text-xl text-slate-900 mt-1">₹{fmt(o.price_per_night)}</p>
                    <p className="text-[11px] text-slate-500">per night</p>
                  </div>
                  <Button size="sm" variant={isSelected ? "default" : "outline"} data-testid={`select-${o.id}`}>
                    {isSelected ? "Selected" : "Select"}
                  </Button>
                </div>
              </div>
            )}

            {intent === "flight" && (
              <div className="flex flex-col sm:flex-row justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Plane className="w-4 h-4 text-blue-600" />
                    <h4 className="font-heading font-bold text-slate-900">{o.airline}</h4>
                    <Badge variant="outline" className="text-[10px] font-mono">{o.flight_no}</Badge>
                    <Badge variant="outline" className="text-[10px]">{o.class}</Badge>
                  </div>
                  <div className="flex items-center gap-3 mt-3">
                    <div>
                      <p className="font-heading font-bold text-lg text-slate-900">{o.departure}</p>
                      <p className="text-[11px] text-slate-500 max-w-[140px] leading-tight">{o.source_airport}</p>
                    </div>
                    <div className="flex-1 flex flex-col items-center">
                      <ArrowRight className="w-5 h-5 text-blue-400" />
                      <span className="text-[10px] text-slate-400 mt-1">{o.duration}</span>
                    </div>
                    <div className="text-right">
                      <p className="font-heading font-bold text-lg text-slate-900">{o.arrival}</p>
                      <p className="text-[11px] text-slate-500 max-w-[140px] leading-tight">{o.destination_airport}</p>
                    </div>
                  </div>
                  <p className="text-xs text-slate-500 mt-2 flex items-center gap-2">
                    <Users className="w-3 h-3" />{o.seats_available} seats left
                  </p>
                  <Provider opt={o} />
                </div>
                <div className="text-right flex sm:flex-col items-end justify-between sm:ml-4 sm:min-w-[120px]">
                  <div>
                    <PriceBadges opt={o} />
                    <p className="font-heading font-extrabold text-xl text-slate-900 mt-1">₹{fmt(o.price)}</p>
                    <p className="text-[11px] text-slate-500">per passenger</p>
                  </div>
                  <Button size="sm" variant={isSelected ? "default" : "outline"} data-testid={`select-${o.id}`}>
                    {isSelected ? "Selected" : "Select"}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        );
      })}
      <p className="text-[11px] text-slate-500 pt-1">
        Note: These comparison results come from AURA's simulated multi-provider index for demo purposes. No real inventory is being queried.
      </p>
    </div>
  );
}
