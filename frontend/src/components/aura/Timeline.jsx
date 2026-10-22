import { Check, Loader2, Circle, X } from "lucide-react";

const STATUS_STYLES = {
  done: "bg-emerald-500 text-white border-emerald-500",
  "in-progress": "bg-indigo-500 text-white border-indigo-500 animate-pulse",
  pending: "bg-white text-slate-400 border-slate-300",
  failed: "bg-rose-500 text-white border-rose-500",
};

const Icon = ({ status }) => {
  if (status === "done") return <Check className="w-3 h-3" />;
  if (status === "in-progress") return <Loader2 className="w-3 h-3 animate-spin" />;
  if (status === "failed") return <X className="w-3 h-3" />;
  return <Circle className="w-2 h-2" />;
};

export default function Timeline({ steps = [] }) {
  return (
    <ol className="space-y-3" data-testid="execution-timeline">
      {steps.map((s, i) => (
        <li key={i} className="flex items-start gap-3 slide-in" data-testid={`timeline-step-${i}`}>
          <div className="flex flex-col items-center">
            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${STATUS_STYLES[s.status] || STATUS_STYLES.pending}`}>
              <Icon status={s.status} />
            </div>
            {i !== steps.length - 1 && (
              <div className={`w-0.5 h-6 mt-1 ${s.status === "done" ? "bg-emerald-300" : "bg-slate-200"}`} />
            )}
          </div>
          <div className="flex-1 pt-0.5">
            <p className={`text-sm font-medium ${s.status === "done" ? "text-slate-900" : s.status === "in-progress" ? "text-indigo-700" : "text-slate-500"}`}>
              {s.step || s.tool}
            </p>
            <p className="text-[11px] text-slate-400 capitalize mt-0.5">{s.status}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
