import { useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Monitor, X } from "lucide-react";

const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = 10;

// Deterministic pseudo-random booked seats per cinema id
function hashedBooked(seedStr) {
  let h = 0;
  for (let i = 0; i < seedStr.length; i++) {
    h = (h * 31 + seedStr.charCodeAt(i)) & 0xffffffff;
  }
  const booked = new Set();
  const target = 18 + (Math.abs(h) % 14); // 18-31 random seats booked
  let x = Math.abs(h) || 1;
  while (booked.size < target) {
    x = (x * 1664525 + 1013904223) & 0xffffffff;
    const r = ROWS[Math.abs(x) % ROWS.length];
    x = (x * 1664525 + 1013904223) & 0xffffffff;
    const c = (Math.abs(x) % COLS) + 1;
    booked.add(`${r}${c}`);
  }
  return booked;
}

export default function SeatPicker({ option, requiredCount, selectedSeats, onSelectedSeatsChange, onBack }) {
  const booked = useMemo(() => hashedBooked(option?.id || "default"), [option?.id]);

  const toggleSeat = (seat) => {
    if (booked.has(seat)) return;
    if (selectedSeats.includes(seat)) {
      onSelectedSeatsChange(selectedSeats.filter((s) => s !== seat));
    } else {
      if (selectedSeats.length >= requiredCount) {
        // replace oldest
        onSelectedSeatsChange([...selectedSeats.slice(1), seat]);
      } else {
        onSelectedSeatsChange([...selectedSeats, seat]);
      }
    }
  };

  return (
    <Card className="p-5 bg-white border-slate-200" data-testid="seat-picker">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-heading font-bold text-slate-900">Pick your seats</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {option.cinema} · {option.screen} · {option.time} · Select {requiredCount} seat{requiredCount > 1 ? "s" : ""}
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onBack} data-testid="seat-back-btn">
          <X className="w-4 h-4 mr-1" />Change show
        </Button>
      </div>

      {/* Screen */}
      <div className="mb-4">
        <div className="h-1.5 bg-gradient-to-r from-indigo-400/10 via-indigo-500 to-indigo-400/10 rounded-full" />
        <p className="text-center text-[10px] uppercase tracking-widest text-slate-400 mt-1 flex items-center justify-center gap-1">
          <Monitor className="w-3 h-3" /> Screen this way
        </p>
      </div>

      {/* Seat grid */}
      <div className="overflow-x-auto scrollbar-thin">
        <div className="inline-block mx-auto">
          {ROWS.map((row) => (
            <div key={row} className="flex items-center gap-1.5 mb-1.5">
              <span className="w-5 text-[11px] font-mono text-slate-400">{row}</span>
              {Array.from({ length: COLS }, (_, i) => i + 1).map((n) => {
                const seat = `${row}${n}`;
                const isBooked = booked.has(seat);
                const isSelected = selectedSeats.includes(seat);
                const aisle = n === 5 ? "mr-3" : "";
                let cls = "border-slate-300 bg-white text-slate-700 hover:border-indigo-400";
                if (isBooked) cls = "border-slate-200 bg-slate-200 text-slate-400 cursor-not-allowed";
                else if (isSelected) cls = "border-indigo-600 bg-indigo-600 text-white";
                return (
                  <button
                    key={seat}
                    onClick={() => toggleSeat(seat)}
                    disabled={isBooked}
                    className={`w-7 h-7 rounded-md border text-[10px] font-semibold transition-colors ${cls} ${aisle}`}
                    data-testid={`seat-${seat}`}
                    aria-label={`Seat ${seat}${isBooked ? " booked" : isSelected ? " selected" : ""}`}
                  >
                    {n}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 text-[11px] text-slate-600">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded border border-slate-300 bg-white inline-block" />Available</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-indigo-600 inline-block" />Selected</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-slate-200 inline-block" />Booked</span>
      </div>

      {/* Status */}
      <div className="mt-4 flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2">
        <div className="text-sm">
          <span className="text-slate-500">Selected: </span>
          <span className="font-mono font-semibold text-slate-900" data-testid="selected-seats-text">
            {selectedSeats.length ? selectedSeats.join(", ") : "—"}
          </span>
        </div>
        <span className="text-xs text-slate-500">
          {selectedSeats.length} / {requiredCount}
        </span>
      </div>
    </Card>
  );
}
