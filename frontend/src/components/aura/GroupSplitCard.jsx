import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const fmt = (amount) => new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
}).format(amount || 0);
const ceilRupee = (amount) => Math.ceil(amount);

export default function GroupSplitCard({
  title,
  travelers,
  lines,
  rooms,
  onRoomsChange,
  namesText = "",
  onNamesChange,
}) {
  const [mode, setMode] = useState("equal");
  const [shareType, setShareType] = useState("amount");
  const [shares, setShares] = useState({});
  const [copyStatus, setCopyStatus] = useState("");
  const people = Math.max(1, Number(travelers) || 1);
  const names = useMemo(
    () => namesText.split(",").map((name) => name.trim()).filter(Boolean),
    [namesText],
  );
  const total = lines.reduce((sum, line) => sum + line.total, 0);
  const equalShare = ceilRupee(total / people);
  const shareValues = Array.from({ length: people }, (_, index) => (
    Number(shares[index]) || 0
  ));
  const shareSum = shareValues.reduce((sum, share) => sum + share, 0);
  const customDifference = shareType === "percent"
    ? 100 - shareSum
    : total - shareSum;
  const customValid = Math.abs(customDifference) < 0.01;
  const perPersonAmounts = shareType === "percent"
    ? shareValues.map((percent) => Math.round(total * percent) / 100)
    : shareValues;

  useEffect(() => {
    setShares({});
  }, [people, total, shareType]);

  const copySummary = async () => {
    const summary = mode === "custom"
      ? customValid
        ? `${title}, ${people} people. Total Rs ${fmt(total)}. ${perPersonAmounts.map(
          (amount, index) => `${names[index] || `Person ${index + 1}`} pays Rs ${fmt(amount)}`,
        ).join(". ")}.`
        : `${title}, ${people} people. Total Rs ${fmt(total)}. Custom split is unbalanced by ${shareType === "percent" ? `${fmt(customDifference)}%` : `Rs ${fmt(customDifference)}`}.`
      : `${title}, ${people} people. Total Rs ${fmt(total)}. Each pays Rs ${fmt(equalShare)}.`;
    try {
      await navigator.clipboard.writeText(summary);
      setCopyStatus("Split summary copied.");
    } catch {
      setCopyStatus("Clipboard access is unavailable in this browser.");
    }
  };

  return (
    <Card className="p-4 border-indigo-200 bg-white space-y-3" data-testid="group-split-card">
      <div>
        <h4 className="font-heading font-bold text-slate-900">Split the cost</h4>
        <p className="text-xs text-slate-500">{people} travelers · totals use the selected mock options</p>
      </div>
      {lines.map((line) => (
        <div key={line.label} className="flex justify-between gap-3 text-sm">
          <span className="text-slate-700">
            {line.label}
            <span className="block text-xs text-slate-500">
              {line.shared
                ? `Shared · about Rs ${fmt(ceilRupee(line.total / people))} per person`
                : `Per person · Rs ${fmt(line.perPerson)} each`}
            </span>
          </span>
          <span className="font-medium text-slate-800">Rs {fmt(line.total)}</span>
        </div>
      ))}

      {lines.some((line) => line.label.toLowerCase().includes("stay")) && (
        <div className="flex items-center gap-2">
          <Label htmlFor="split-rooms" className="text-xs text-slate-600">Hotel rooms</Label>
          <Input
            id="split-rooms"
            type="number"
            min={1}
            max={people}
            value={rooms}
            onChange={(event) => onRoomsChange(Math.min(people, Math.max(1, Number(event.target.value) || 1)))}
            className="h-8 w-20"
          />
          <span className="text-xs text-slate-500">(2 people per room by default)</span>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant={mode === "equal" ? "default" : "outline"} onClick={() => setMode("equal")}>
          Split equally
        </Button>
        <Button size="sm" variant={mode === "custom" ? "default" : "outline"} onClick={() => setMode("custom")}>
          Custom split
        </Button>
      </div>

      <div>
        <Label htmlFor="split-names" className="text-xs text-slate-600">Traveler names (optional, comma-separated)</Label>
        <Input
          id="split-names"
          value={namesText}
          onChange={(event) => onNamesChange(event.target.value)}
          placeholder="Rahul, Aman, Priya"
          className="mt-1"
        />
      </div>

      {mode === "equal" ? (
        <div className="space-y-1">
          {Array.from({ length: people }, (_, index) => (
            <p key={index} className="flex justify-between text-sm text-slate-700">
              <span>{names[index] || `Person ${index + 1}`}</span>
              <span>Rs {fmt(equalShare)}</span>
            </p>
          ))}
          <p className="text-[11px] text-slate-500">Rounded up to the next rupee; final settlement may differ by rounding.</p>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label htmlFor="split-type" className="text-xs text-slate-600">Custom share format</Label>
            <select
              id="split-type"
              className="h-8 rounded-md border border-slate-300 bg-white px-2 text-sm"
              value={shareType}
              onChange={(event) => setShareType(event.target.value)}
            >
              <option value="amount">Amount (Rs)</option>
              <option value="percent">Percentage (%)</option>
            </select>
          </div>
          {Array.from({ length: people }, (_, index) => (
            <div key={index} className="grid grid-cols-[1fr_110px] gap-2 items-center">
              <span className="text-sm text-slate-700">{names[index] || `Person ${index + 1}`}</span>
              <Input
                type="number"
                min={0}
                step="any"
                value={shares[index] || ""}
                aria-label={`Share for ${names[index] || `Person ${index + 1}`}`}
                onChange={(event) => setShares((current) => ({
                  ...current,
                  [index]: event.target.value,
                }))}
                placeholder={shareType === "percent" ? "%" : "Rs"}
                className="h-8"
              />
              {shareType === "percent" && shares[index] && (
                <span className="col-span-2 text-right text-xs text-slate-500">
                  Rs {fmt(perPersonAmounts[index])}
                </span>
              )}
            </div>
          ))}
          <p className={`text-sm ${customValid ? "text-emerald-700" : "text-amber-800"}`}>
            {customValid
              ? "Custom shares add up to the grand total."
              : `Remaining ${shareType === "percent" ? `${fmt(customDifference)}%` : `Rs ${fmt(customDifference)}`} to balance.`}
          </p>
        </div>
      )}

      <div className="border-t border-slate-200 pt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {mode === "equal" ? "Each person pays" : "Custom split amounts"}
        </p>
        {mode === "equal" && (
          <p className="font-heading text-2xl font-extrabold text-indigo-700">Rs {fmt(equalShare)}</p>
        )}
        <p className="text-sm font-bold text-slate-800 mt-1">Grand total: Rs {fmt(total)}</p>
        {mode === "custom" && customValid && (
          <div className="mt-2 space-y-1">
            {perPersonAmounts.map((amount, index) => (
              <p key={index} className="flex justify-between text-sm text-slate-700">
                <span>{names[index] || `Person ${index + 1}`}</span>
                <span>Rs {fmt(amount)}</span>
              </p>
            ))}
          </div>
        )}
      </div>
      <Button size="sm" variant="outline" onClick={copySummary} className="w-full">
        Copy split summary
      </Button>
      {copyStatus && <p role="status" className="text-xs text-slate-600">{copyStatus}</p>}
    </Card>
  );
}
