import { useEffect, useRef, useState } from "react";
import { Sparkles, Send, Film, Hotel, Plane, RefreshCw, History, Zap, Info } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { chat, searchOptions, confirmBooking, createBooking, listBookings } from "@/lib/api";
import Timeline from "@/components/aura/Timeline";
import ParametersCard from "@/components/aura/ParametersCard";
import OptionList from "@/components/aura/OptionList";
import ConfirmationCard from "@/components/aura/ConfirmationCard";
import BookingReceipt from "@/components/aura/BookingReceipt";
import HistoryList from "@/components/aura/HistoryList";

const INTENT_ICON = { movie: Film, hotel: Hotel, flight: Plane };
const INTENT_COLOR = {
  movie: "bg-rose-100 text-rose-700 border-rose-200",
  hotel: "bg-emerald-100 text-emerald-700 border-emerald-200",
  flight: "bg-blue-100 text-blue-700 border-blue-200",
  unknown: "bg-slate-100 text-slate-700 border-slate-200",
};

const PRESETS = [
  { label: "Movie tickets in Bhilai", text: "Book 2 tickets for Mirzapur tomorrow evening in Bhilai", intent: "movie", testid: "prompt-preset-movie" },
  { label: "Hotel in Raipur", text: "Book a hotel in Raipur for 2 nights from 15 October for 2 guests", intent: "hotel", testid: "prompt-preset-hotel" },
  { label: "Flight Raipur → Delhi", text: "Find a flight from Raipur to Delhi on 20 October for 1 passenger", intent: "flight", testid: "prompt-preset-flight" },
];

const STEP_ORDER = ["Understand request", "Extract parameters", "Search", "Present options", "Await user selection", "Calculate price", "Confirm & create mock booking", "Verify booking"];

export default function AuraApp() {
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatResp, setChatResp] = useState(null);
  const [options, setOptions] = useState([]);
  const [quantity, setQuantity] = useState(1);
  const [nights, setNights] = useState(1);
  const [selected, setSelected] = useState(null);
  const [preview, setPreview] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [plan, setPlan] = useState([]);
  const [history, setHistory] = useState([]);
  const [tab, setTab] = useState("agent");
  const resultsRef = useRef(null);

  const intent = chatResp?.intent || "unknown";
  const IntentIcon = INTENT_ICON[intent] || Sparkles;

  const refreshHistory = async () => {
    try {
      const data = await listBookings();
      setHistory(data.bookings || []);
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    refreshHistory();
  }, []);

  const updateStep = (stepName, status, basePlan) => {
    const source = basePlan || plan;
    const updated = source.map((p) => {
      if (p.step.toLowerCase().startsWith(stepName.toLowerCase())) {
        return { ...p, status };
      }
      return p;
    });
    setPlan(updated);
    return updated;
  };

  const resetFlow = () => {
    setChatResp(null);
    setOptions([]);
    setSelected(null);
    setPreview(null);
    setReceipt(null);
    setPlan([]);
    setQuantity(1);
    setNights(1);
  };

  const submitGoal = async (text) => {
    const message = (text ?? goal).trim();
    if (!message) {
      toast.error("Please enter a request first");
      return;
    }
    resetFlow();
    setLoading(true);
    try {
      const data = await chat(message);
      setChatResp(data);
      setPlan(data.plan || []);
      // Default quantities from params
      const q = data?.params?.tickets || data?.params?.passengers || data?.params?.guests || 1;
      setQuantity(q);
      if (data.intent === "hotel") setNights(data?.params?.nights || 1);

      if (data.missing && data.missing.length) {
        toast.warning(data.missing[0]);
        return;
      }
      if (data.ready_to_search) {
        await runSearch(data);
      }
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (e) {
      console.error(e);
      toast.error("Failed to parse request");
    } finally {
      setLoading(false);
    }
  };

  const runSearch = async (data) => {
    const basePlan = updateStep("Search", "in-progress", data.plan);
    try {
      const res = await searchOptions(data.intent, data.params);
      setOptions(res.results || []);
      const p2 = basePlan.map((p) => {
        if (p.step.toLowerCase().startsWith("search")) return { ...p, status: "done" };
        if (p.step.toLowerCase().startsWith("present options")) return { ...p, status: "done" };
        if (p.step.toLowerCase().startsWith("await user selection")) return { ...p, status: "in-progress" };
        return p;
      });
      setPlan(p2);
      if (!res.results?.length) toast.info("No options found for your query");
    } catch (e) {
      toast.error("Search failed");
    }
  };

  const handleSelect = async (opt) => {
    setSelected(opt);
    updateStep("Await user selection", "done");
    updateStep("Calculate price", "in-progress");
    try {
      const data = await confirmBooking({
        intent,
        option_id: opt.id,
        quantity: Number(quantity) || 1,
        nights: Number(nights) || 1,
      });
      setPreview(data);
      updateStep("Calculate price", "done");
      toast.success("Price calculated. Please confirm.");
    } catch (e) {
      toast.error("Failed to calculate price");
    }
  };

  const handleQuantityChange = async (newQty) => {
    setQuantity(newQty);
    if (selected) {
      try {
        const data = await confirmBooking({
          intent,
          option_id: selected.id,
          quantity: Number(newQty) || 1,
          nights: Number(nights) || 1,
        });
        setPreview(data);
      } catch (_) {}
    }
  };

  const handleNightsChange = async (newNights) => {
    setNights(newNights);
    if (selected) {
      try {
        const data = await confirmBooking({
          intent,
          option_id: selected.id,
          quantity: Number(quantity) || 1,
          nights: Number(newNights) || 1,
        });
        setPreview(data);
      } catch (_) {}
    }
  };

  const handleConfirm = async () => {
    if (!selected || !preview) return;
    updateStep("Confirm & create mock booking", "in-progress");
    try {
      const data = await createBooking({
        intent,
        option_id: selected.id,
        quantity: Number(quantity) || 1,
        nights: Number(nights) || 1,
        confirmed: true,
        user_request: goal,
      });
      setReceipt(data);
      const p = plan.map((s) => {
        if (s.step.toLowerCase().startsWith("confirm & create")) return { ...s, status: "done" };
        if (s.step.toLowerCase().startsWith("verify")) return { ...s, status: data.verified ? "done" : "failed" };
        return s;
      });
      setPlan(p);
      toast.success("Simulated booking confirmed!");
      await refreshHistory();
    } catch (e) {
      toast.error("Booking failed");
      updateStep("Confirm & create mock booking", "failed");
    }
  };

  const handleCancel = () => {
    setSelected(null);
    setPreview(null);
    updateStep("Await user selection", "in-progress");
    toast.info("Selection cancelled");
  };

  return (
    <div className="min-h-screen w-full overflow-x-hidden">
      {/* Header */}
      <header className="border-b border-slate-200/70 backdrop-blur-md bg-white/70 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-500 flex items-center justify-center text-white aura-pulse">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-heading text-xl sm:text-2xl font-extrabold text-slate-900">AURA</h1>
              <p className="text-xs text-slate-500 -mt-0.5">Autonomous Universal Resource Agent</p>
            </div>
          </div>
          <Badge variant="outline" className="hidden sm:inline-flex border-amber-300 bg-amber-50 text-amber-800">
            <Info className="w-3 h-3 mr-1" /> Demo — bookings are simulated
          </Badge>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList className="mb-6" data-testid="main-tabs">
            <TabsTrigger value="agent" data-testid="tab-agent"><Zap className="w-4 h-4 mr-1.5" />Agent</TabsTrigger>
            <TabsTrigger value="history" data-testid="past-bookings-tab" onClick={refreshHistory}><History className="w-4 h-4 mr-1.5" />History</TabsTrigger>
          </TabsList>

          <TabsContent value="agent">
            {/* Hero / Input */}
            <section className="mb-6">
              <h2 className="font-heading text-2xl sm:text-3xl md:text-4xl font-extrabold text-slate-900 mb-2">
                Tell AURA your plan.
              </h2>

              <div className="mt-5 flex flex-col sm:flex-row gap-2">
                <Input
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && submitGoal()}
                  placeholder="e.g. Book 2 movie tickets for tomorrow evening in Bhilai"
                  className="h-12 text-sm sm:text-base"
                  data-testid="goal-input"
                />
                <Button
                  onClick={() => submitGoal()}
                  disabled={loading}
                  className="h-12 px-6 bg-indigo-600 hover:bg-indigo-700 text-white"
                  data-testid="submit-goal-btn"
                >
                  {loading ? <RefreshCw className="w-4 h-4 animate-spin mr-1.5" /> : <Send className="w-4 h-4 mr-1.5" />}
                  Run Agent
                </Button>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <span className="text-xs text-slate-500 self-center mr-1">Quick demos:</span>
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => { setGoal(p.text); submitGoal(p.text); }}
                    className="text-xs px-3 py-1.5 rounded-full border border-slate-200 bg-white hover:border-indigo-400 hover:text-indigo-700 transition-colors"
                    data-testid={p.testid}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </section>

            {/* Agent workflow */}
            {chatResp && (
              <section ref={resultsRef} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left: Timeline */}
                <aside className="lg:col-span-4 space-y-4">
                  <Card className="p-4 bg-white border-slate-200">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-heading font-bold text-slate-900">Execution Timeline</h3>
                      <Badge className={`${INTENT_COLOR[intent]} border capitalize`}>
                        <IntentIcon className="w-3 h-3 mr-1" />{intent}
                      </Badge>
                    </div>
                    <Timeline steps={plan} />
                    {chatResp.parser_source && (
                      <p className="text-[11px] text-slate-400 mt-3 font-mono">
                        parser: {chatResp.parser_source}
                      </p>
                    )}
                  </Card>
                </aside>

                {/* Right: dynamic content */}
                <section className="lg:col-span-8 space-y-5">
                  <ParametersCard intent={intent} params={chatResp.params || {}} missing={chatResp.missing || []} />

                  {!receipt && options.length > 0 && (
                    <OptionList
                      intent={intent}
                      options={options}
                      selectedId={selected?.id}
                      onSelect={handleSelect}
                    />
                  )}

                  {!receipt && selected && preview && (
                    <ConfirmationCard
                      intent={intent}
                      option={selected}
                      quantity={quantity}
                      nights={nights}
                      preview={preview}
                      onQuantityChange={handleQuantityChange}
                      onNightsChange={handleNightsChange}
                      onConfirm={handleConfirm}
                      onCancel={handleCancel}
                    />
                  )}

                  {receipt && (
                    <BookingReceipt
                      receipt={receipt}
                      onNew={() => { resetFlow(); setGoal(""); }}
                    />
                  )}
                </section>
              </section>
            )}

            {!chatResp && (
              <section className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
                {PRESETS.map((p) => {
                  const Icon = INTENT_ICON[p.intent];
                  return (
                    <Card key={p.label} className="p-5 bg-white hover:border-indigo-400 transition-colors cursor-pointer"
                          onClick={() => { setGoal(p.text); submitGoal(p.text); }}>
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${INTENT_COLOR[p.intent]}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <h4 className="font-heading font-bold text-slate-900 text-base mb-1 capitalize">{p.intent} demo</h4>
                      <p className="text-xs text-slate-500 leading-relaxed">{p.text}</p>
                    </Card>
                  );
                })}
              </section>
            )}
          </TabsContent>

          <TabsContent value="history">
            <HistoryList bookings={history} onRefresh={refreshHistory} />
          </TabsContent>
        </Tabs>

        <footer className="mt-16 py-6 border-t border-slate-200 text-center text-xs text-slate-500">
          AURA · a college project by B.Tech students · All bookings are simulated.
        </footer>
      </main>
    </div>
  );
}
