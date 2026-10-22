import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MapPin, Calendar, Clock, Users, Film, Hotel, Plane, AlertTriangle, Info as InfoIcon } from "lucide-react";

const LABELS = {
  movie: "Movie Booking",
  hotel: "Hotel Booking",
  flight: "Flight Booking",
  train: "Train Search",
  bus: "Bus Search",
  concert: "Concert Search",
  cricket: "Cricket Search",
  trip: "Trip Plan",
  trip_planner: "Trip Plan",
  budget_optimizer: "Budget Plan",
  unknown: "Not Understood",
};

const COLORS = {
  movie: "bg-rose-50 text-rose-700 border-rose-200",
  hotel: "bg-emerald-50 text-emerald-700 border-emerald-200",
  flight: "bg-blue-50 text-blue-700 border-blue-200",
  train: "bg-blue-50 text-blue-700 border-blue-200",
  bus: "bg-blue-50 text-blue-700 border-blue-200",
  concert: "bg-purple-50 text-purple-700 border-purple-200",
  cricket: "bg-amber-50 text-amber-700 border-amber-200",
  trip: "bg-indigo-50 text-indigo-700 border-indigo-200",
  trip_planner: "bg-indigo-50 text-indigo-700 border-indigo-200",
  budget_optimizer: "bg-emerald-50 text-emerald-700 border-emerald-200",
  unknown: "bg-slate-50 text-slate-700 border-slate-200",
};

const Row = ({ icon: Icon, label, value }) => (
  <div className="flex items-start gap-2 text-sm">
    <Icon className="w-4 h-4 text-slate-400 mt-0.5" />
    <div>
      <span className="text-slate-500">{label}: </span>
      <span className="font-medium text-slate-900">{value ?? <em className="text-slate-400">—</em>}</span>
    </div>
  </div>
);

export default function ParametersCard({ intent, params, missing }) {
  return (
    <Card className="p-5 bg-white border-slate-200" data-testid="parameters-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-heading font-bold text-slate-900">Extracted Parameters</h3>
        <Badge className={`${COLORS[intent]} border capitalize`}>{LABELS[intent]}</Badge>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {intent === "movie" && (
          <>
            <Row icon={Film} label="Movie" value={params.movie} />
            <Row icon={MapPin} label="City" value={params.city} />
            <Row icon={Calendar} label="Date" value={params.date} />
            <Row icon={Clock} label="When" value={params.time_window} />
            <Row icon={Users} label="Tickets" value={params.tickets} />
          </>
        )}
        {intent === "hotel" && (
          <>
            <Row icon={Hotel} label="Stay type" value="Hotel" />
            <Row icon={MapPin} label="City" value={params.city} />
            <Row icon={Calendar} label="Check-in" value={params.check_in} />
            <Row icon={Clock} label="Nights" value={params.nights} />
            <Row icon={Users} label="Guests" value={params.guests} />
          </>
        )}
        {intent === "flight" && (
          <>
            <Row icon={Plane} label="From" value={params.source} />
            <Row icon={Plane} label="To" value={params.destination} />
            <Row icon={Calendar} label="Travel date" value={params.date} />
            <Row icon={Clock} label="When" value={params.time_window} />
            <Row icon={Users} label="Passengers" value={params.passengers} />
          </>
        )}
        {!["movie", "hotel", "flight"].includes(intent) &&
          Object.entries(params || {}).filter(([, value]) => value != null && value !== "").map(([key, value]) => (
            <Row key={key} icon={InfoIcon} label={key.replaceAll("_", " ")} value={String(value)} />
          ))}
      </div>
      {missing?.length > 0 && (
        <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-900">AURA needs more info:</p>
            <ul className="list-disc pl-5 text-sm text-amber-800 mt-1">
              {missing.map((m, i) => <li key={i}>{m}</li>)}
            </ul>
          </div>
        </div>
      )}
    </Card>
  );
}
