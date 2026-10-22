import { useCallback, useEffect, useRef, useState } from "react";
import {
  Sparkles, Send, Film, Hotel, Plane, RefreshCw, History, Zap, Info,
  Mic, MicOff, Train, Bus, Music, Trophy, Wallet, Map, LogOut,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  approvePlan, chat, confirmBooking, confirmPlanBooking, conversationalChat, createBooking, executeStep, formatApiError, getHistory,
} from "@/lib/api";
import {
  abortConversationRequest,
  normalizeConversationPlan,
  runConversationRequest,
} from "@/lib/conversationRequest";
import Timeline from "@/components/aura/Timeline";
import ParametersCard from "@/components/aura/ParametersCard";
import HistoryList from "@/components/aura/HistoryList";
import OptionList from "@/components/aura/OptionList";
import SeatPicker from "@/components/aura/SeatPicker";
import ConfirmationCard from "@/components/aura/ConfirmationCard";
import BookingReceipt from "@/components/aura/BookingReceipt";
import ConversationPanel from "@/components/aura/ConversationPanel";

const TOOL_ICON = {
  movie: Film, hotel: Hotel, flight: Plane, train: Train, bus: Bus,
  concert: Music, cricket: Trophy, trip: Map, trip_planner: Map,
  budget_optimizer: Wallet,
};
const TOOL_COLOR = {
  movie: "bg-rose-100 text-rose-700 border-rose-200",
  hotel: "bg-emerald-100 text-emerald-700 border-emerald-200",
  flight: "bg-blue-100 text-blue-700 border-blue-200",
  train: "bg-blue-100 text-blue-700 border-blue-200",
  bus: "bg-blue-100 text-blue-700 border-blue-200",
  concert: "bg-purple-100 text-purple-700 border-purple-200",
  cricket: "bg-amber-100 text-amber-700 border-amber-200",
  trip: "bg-indigo-100 text-indigo-700 border-indigo-200",
  trip_planner: "bg-indigo-100 text-indigo-700 border-indigo-200",
  budget_optimizer: "bg-emerald-100 text-emerald-700 border-emerald-200",
  unknown: "bg-slate-100 text-slate-700 border-slate-200",
};
const BOOKING_TOOLS = ["movie", "hotel", "flight", "train", "bus", "cricket", "concert"];
const BOOKING_TIMELINE = [
  { step: "Understand request", status: "done" },
  { step: "Extract parameters", status: "done" },
  { step: "Search", status: "pending" },
  { step: "Confirm and create mock booking", status: "pending" },
  { step: "Verify booking", status: "pending" },
];
const PRESETS = [
  { label: "Movie tickets in Bhilai", title: "Movie Demo", text: "Book 2 tickets for Mirzapur tomorrow evening in Bhilai", tool: "movie" },
  { label: "Hotel in Raipur", title: "Hotel Demo", text: "Book a hotel in Raipur for 2 nights from 15 October for 2 guests", tool: "hotel" },
  { label: "Flight Raipur → Delhi", title: "Flight Demo", text: "Find a flight from Raipur to Delhi on 20 October for 1 passenger", tool: "flight" },
  { label: "Train Delhi → Agra", title: "Train Demo", text: "Book a train from Delhi to Agra on 18 October for 2 passengers", tool: "train" },
  { label: "Cricket in Mumbai", title: "Cricket Demo", text: "Cricket tickets for India vs Australia in Mumbai on 20 October for 3", tool: "cricket" },
  { label: "Plan a Goa trip", title: "Trip Planner Demo", text: "Plan a trip to Goa for 3 nights from Delhi starting 20 October", tool: "trip_planner" },
];
const toolLabel = (name = "") => name.replace(/_/g, " ");

export default function AuraApp({ user, authEnabled = true, onLogout }) {
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatResp, setChatResp] = useState(null);
  const [plan, setPlan] = useState([]);
  const [results, setResults] = useState([]);
  const [options, setOptions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [selectedIntent, setSelectedIntent] = useState(null);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [quantity, setQuantity] = useState(1);
  const [nights, setNights] = useState(1);
  const [rooms, setRooms] = useState(1);
  const [preview, setPreview] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [history, setHistory] = useState({ bookings: [], runs: [] });
  const [tab, setTab] = useState("agent");
  const [pendingRequest, setPendingRequest] = useState(null);
  const [approved, setApproved] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const userId = user.id;
  const [experience, setExperience] = useState("chat");
  const [conversationInput, setConversationInput] = useState("");
  const [conversation, setConversation] = useState(() => {
    try {
      const stored = JSON.parse(window.localStorage.getItem(`aura-chat-${userId}`) || "[]");
      return Array.isArray(stored) ? stored : [];
    } catch {
      return [];
    }
  });
  const [conversationReset, setConversationReset] = useState(false);
  const conversationRequestRef = useRef(null);
  const [tripPlan, setTripPlan] = useState(null);
  const [tripSelections, setTripSelections] = useState({});
  const [eventBookings, setEventBookings] = useState([]);
  const [eventCheckout, setEventCheckout] = useState(null);
  const [eventPlanStatus, setEventPlanStatus] = useState("idle");
  const [eventPlanError, setEventPlanError] = useState("");
  const [hubTool] = useState(() => {
    const query = new URLSearchParams(window.location.search);
    return query.get("tool") || query.get("feature") || "";
  });
  const resultsRef = useRef(null);

  useEffect(() => () => abortConversationRequest(conversationRequestRef), []);

  const intent = chatResp?.intent || "unknown";
  const IntentIcon = TOOL_ICON[intent] || Sparkles;

  const refreshHistory = useCallback(async () => {
    try {
      const data = await getHistory(userId);
      setHistory({ bookings: data.bookings || [], runs: data.runs || [] });
    } catch (error) {
      toast.error(`Could not load history: ${formatApiError(error)}`);
    }
  }, [userId]);

  useEffect(() => {
    refreshHistory();
    setSpeechSupported(Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
  }, [refreshHistory]);

  const resetFlow = () => {
    setChatResp(null);
    setPlan([]);
    setResults([]);
    setOptions([]);
    setSelected(null);
    setSelectedIntent(null);
    setSelectedSeats([]);
    setQuantity(1);
    setNights(1);
    setPreview(null);
    setReceipt(null);
    setEventCheckout(null);
    setEventPlanStatus("idle");
    setApproved(false);
  };

  const submitGoal = async (text, selectedTool = hubTool) => {
    const answer = (text ?? goal).trim();
    if (!answer) {
      toast.error("Please enter a request first");
      return;
    }
    const requestText = pendingRequest
      ? `${pendingRequest.message} Additional details: ${answer}`
      : answer;
    const requestTool = pendingRequest?.tool || selectedTool || undefined;
    resetFlow();
    setLoading(true);
    try {
      const data = await chat(requestText, userId, requestTool);
      setChatResp(data);
      const toolSteps = (data.steps || []).map((step) => ({
        ...step,
        step: toolLabel(step.tool),
      }));
      const hasBookingFlow = data.steps?.length === 1
        && BOOKING_TOOLS.includes(data.steps[0].tool);
      if (hasBookingFlow) {
        setPlan(BOOKING_TIMELINE);
        const params = data.steps[0].parameters || {};
        setQuantity(params.tickets || params.passengers || params.guests || 1);
        setNights(params.nights || 1);
      } else {
        setPlan(toolSteps);
      }
      if (data.missing?.length) {
        setPendingRequest({ message: requestText, tool: requestTool });
        setGoal("");
        toast.warning(data.question || data.missing[0]);
      } else {
        setPendingRequest(null);
        setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
      }
      await refreshHistory();
    } catch (error) {
      toast.error(`Could not create plan: ${formatApiError(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const sendConversation = async (text = conversationInput) => {
    const message = text.trim();
    if (!message || loading) return;
    await runConversationRequest(conversationRequestRef, async (signal) => {
      setConversationInput("");
      setLoading(true);
      try {
        const data = await conversationalChat(message, userId, conversation, conversationReset, signal);
        if (signal.aborted) return;
        const nextConversation = data.conversation || [
          ...conversation,
          { role: "user", content: message },
          { role: "assistant", content: data.reply },
        ];
        setConversation(nextConversation);
        window.localStorage.setItem(`aura-chat-${userId}`, JSON.stringify(nextConversation));
        setConversationReset(false);
        if (data.explanation_only) return;
        setTripPlan(normalizeConversationPlan(data.trip_plan, data.run_id));
        setRooms(Math.max(1, Math.ceil((Number(data.trip_plan?.details?.travelers) || 1) / 2)));
        setTripSelections(data.trip_plan?.kind === "event_travel"
          ? data.trip_plan.defaults
          : data.trip_plan?.kind === "destination_trip"
            ? {
              trip_transport: data.trip_plan.selected_defaults.transport
                ? { intent: data.trip_plan.selected_defaults.transport.intent, option: data.trip_plan.selected_defaults.transport }
                : null,
              trip_return: data.trip_plan.selected_defaults.return
                ? { intent: data.trip_plan.selected_defaults.return.intent, option: data.trip_plan.selected_defaults.return }
                : null,
              hotel: { intent: "hotel", option: data.trip_plan.selected_defaults.hotel },
            }
            : {});
        setEventBookings([]);
        setEventCheckout(null);
        setEventPlanStatus("idle");
        setEventPlanError("");
        setSelected(null);
        setSelectedIntent(null);
        setPreview(null);
        setReceipt(null);
        if (data.run_id) {
          setChatResp(data);
          setPlan((data.steps || []).map((step) => ({
            ...step,
            step: toolLabel(step.tool),
          })));
          setResults([]);
          setApproved(false);
        } else {
          setChatResp(null);
          setPlan([]);
          setResults([]);
          setApproved(false);
        }
        await refreshHistory();
      } catch (error) {
        if (!signal.aborted) {
          toast.error(`Could not send message: ${formatApiError(error)}`);
          setConversationInput(message);
        }
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    });
  };

  const resetConversation = () => {
    abortConversationRequest(conversationRequestRef);
    setConversation([]);
    setConversationInput("");
    setConversationReset(true);
    setTripPlan(null);
    setTripSelections({});
    setEventBookings([]);
    setEventCheckout(null);
    setEventPlanStatus("idle");
    setEventPlanError("");
    setSelected(null);
    setSelectedIntent(null);
    setPreview(null);
    setReceipt(null);
    setChatResp(null);
    setPlan([]);
    setResults([]);
    setApproved(false);
    window.localStorage.removeItem(`aura-chat-${userId}`);
  };

  const approveAndRun = async () => {
    if (!chatResp?.run_id || loading) return;
    setLoading(true);
    try {
      await approvePlan(chatResp.run_id, userId);
      setApproved(true);
      const hasBookingFlow = chatResp.steps.length === 1
        && BOOKING_TOOLS.includes(chatResp.steps[0].tool);
      for (let index = 0; index < chatResp.steps.length; index += 1) {
        setPlan((current) => current.map((step, stepIndex) => (
          hasBookingFlow
            ? (step.step === "Search" ? { ...step, status: "in-progress" } : step)
            : (stepIndex === index ? { ...step, status: "in-progress" } : step)
        )));
        try {
          const completed = await executeStep(chatResp.run_id, index, userId);
          setResults((current) => [...current, {
            index,
            tool: completed.tool,
            result: completed.result,
          }]);
          if (hasBookingFlow) {
            setOptions(completed.result.results || []);
            if (!completed.result.results?.length) toast.info("No options found for your query.");
            setPlan((current) => current.map((step, stepIndex) => (
              step.step === "Search"
                ? { ...step, status: "done", result: completed.result }
                : step
            )));
          } else {
            setPlan((current) => current.map((step, stepIndex) => (
              stepIndex === index ? { ...step, status: "done", result: completed.result } : step
            )));
          }
        } catch (error) {
          setPlan((current) => current.map((step, stepIndex) => (
            hasBookingFlow
              ? (step.step === "Search" ? { ...step, status: "failed" } : step)
              : (stepIndex === index ? { ...step, status: "failed" } : step)
          )));
          toast.error(`Step stopped: ${formatApiError(error)}`);
          break;
        }
      }
      await refreshHistory();
    } catch (error) {
      toast.error(`Could not approve plan: ${formatApiError(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const updateBookingStep = (name, status) => {
    setPlan((current) => current.map((step) => (
      step.step === name ? { ...step, status } : step
    )));
  };

  const selectOption = async (option, optionIntent = intent) => {
    setSelected(option);
    setSelectedIntent(optionIntent);
    setSelectedSeats([]);
    setPreview(null);
    const isConversation = chatResp?.mode === "conversation";
    if (isConversation) {
      setTripSelections((current) => ({
        ...current,
        [optionIntent]: { intent: optionIntent, option },
      }));
      setQuantity(Number(tripPlan?.details?.travelers) || 1);
      setNights(Number(tripPlan?.details?.nights) || 3);
      setReceipt(null);
    } else {
      updateBookingStep("Confirm and create mock booking", "in-progress");
    }
    try {
      const data = await confirmBooking({
        intent: optionIntent,
        option_id: option.id,
        quantity: isConversation ? Number(tripPlan?.details?.travelers) || 1 : Number(quantity) || 1,
        nights: isConversation && optionIntent === "hotel"
          ? Number(tripPlan?.details?.nights) || 3
          : Number(nights) || 1,
        rooms: optionIntent === "hotel" ? rooms : 1,
      });
      setPreview(data);
    } catch (error) {
      if (!isConversation) updateBookingStep("Confirm and create mock booking", "failed");
      toast.error(`Price calculation failed: ${formatApiError(error)}`);
    }
  };

  const refreshPreview = async (nextQuantity, nextNights, nextRooms = rooms, promoCode = "", insurance = false) => {
    if (!selected) return;
    try {
      const data = await confirmBooking({
        intent: selectedIntent || intent,
        option_id: selected.id,
        quantity: Number(nextQuantity) || 1,
        nights: Number(nextNights) || 1,
        rooms: selectedIntent === "hotel" || intent === "hotel" ? Number(nextRooms) || 1 : 1,
        promo_code: promoCode,
        insurance,
      });
      setPreview(data);
    } catch (error) {
      toast.error(`Price calculation failed: ${formatApiError(error)}`);
    }
  };

  const confirmMockBooking = async (checkout = {}) => {
    if (!selected || !preview) return;
    const bookingIntent = selectedIntent || intent;
    const isConversation = chatResp?.mode === "conversation";
    if (bookingIntent === "movie" && selectedSeats.length !== Number(quantity)) {
      toast.error(`Please pick exactly ${quantity} seat${quantity > 1 ? "s" : ""}`);
      return;
    }
    if (!isConversation) updateBookingStep("Confirm and create mock booking", "in-progress");
    setLoading(true);
    try {
      if (isConversation && !approved) {
        await approvePlan(chatResp.run_id, userId);
        for (let index = 0; index < chatResp.steps.length; index += 1) {
          setPlan((current) => current.map((step, stepIndex) => (
            stepIndex === index ? { ...step, status: "in-progress" } : step
          )));
          try {
            const completed = await executeStep(chatResp.run_id, index, userId);
            setResults((current) => [...current, {
              index,
              tool: completed.tool,
              result: completed.result,
            }]);
            setPlan((current) => current.map((step, stepIndex) => (
              stepIndex === index ? { ...step, status: "done", result: completed.result } : step
            )));
          } catch (error) {
            setPlan((current) => current.map((step, stepIndex) => (
              stepIndex === index ? { ...step, status: "failed" } : step
            )));
            throw error;
          }
        }
        setApproved(true);
        toast.success("Plan approved and tools completed. Confirm the booking to save it to History.");
        return;
      }
      const booking = await createBooking({
        intent: bookingIntent,
        option_id: selected.id,
        user_id: userId,
        run_id: chatResp.run_id,
        quantity: Number(quantity) || Number(tripPlan?.details?.travelers) || 1,
        nights: bookingIntent === "hotel"
          ? Number(nights) || Number(tripPlan?.details?.nights) || 3
          : 1,
        rooms: bookingIntent === "hotel" ? Number(rooms) || 1 : 1,
        confirmed: true,
        user_request: chatResp.request || goal || pendingRequest?.message,
        seats: bookingIntent === "movie" ? selectedSeats : undefined,
        passengers: checkout.passengers,
        contact: checkout.contact,
        promo_code: checkout.promo_code,
        insurance: checkout.insurance,
        payment_method: checkout.payment_method,
      });
      setReceipt({ ...booking, seats: bookingIntent === "movie" ? selectedSeats : undefined });
      if (isConversation) {
        setTripSelections((current) => ({
          ...current,
          [bookingIntent]: { intent: bookingIntent, option: selected },
        }));
      } else {
        updateBookingStep("Confirm and create mock booking", "done");
        updateBookingStep("Verify booking", booking.verified ? "done" : "failed");
      }
      await refreshHistory();
      toast.success("Simulated booking confirmed!");
    } catch (error) {
      if (!isConversation) updateBookingStep("Confirm and create mock booking", "failed");
      toast.error(`Booking failed: ${formatApiError(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const selectEventOption = (part, selection) => {
    setEventCheckout(null);
    setEventPlanStatus("idle");
    setTripSelections((current) => {
      const next = { ...current, [part]: selection };
      if (part === "outbound") {
        const matchingReturns = tripPlan.options.return.filter(
          (option) => option.intent === selection.intent,
        );
        const matchedReturn = matchingReturns.find((option) => option.recommended)
          || matchingReturns.sort((left, right) => left.price - right.price)[0];
        if (matchedReturn) {
          next.return = { intent: selection.intent, option: matchedReturn };
        }
      }
      return next;
    });
  };

  const selectTripOption = (part, option, optionIntent) => {
    setEventCheckout(null);
    setEventPlanStatus("idle");
    setTripSelections((current) => {
      const next = {
        ...current,
        [part]: { intent: optionIntent, option },
      };
      if (part === "trip_transport") {
        const matchingReturns = tripPlan?.options?.[`${optionIntent}_return`] || [];
        const matchedReturn = matchingReturns.find((item) => item.tier === option.tier)
          || matchingReturns.find((item) => item.recommended)
          || matchingReturns[0];
        next.trip_return = matchedReturn
          ? { intent: optionIntent, option: matchedReturn }
          : null;
      }
      return next;
    });
  };

  const openEventCheckout = async () => {
    if (!tripPlan || eventCheckout || loading) return;
    const travelers = Number(tripPlan.details.travelers) || 1;
    const isDestinationTrip = tripPlan.kind === "destination_trip";
    const selectedItems = isDestinationTrip
      ? [
        ...((tripSelections.trip_transport || (tripPlan.selected_defaults.transport
          ? { intent: tripPlan.selected_defaults.transport.intent, option: tripPlan.selected_defaults.transport }
          : null))
          ? [{ label: "Outbound travel", selection: tripSelections.trip_transport || { intent: tripPlan.selected_defaults.transport.intent, option: tripPlan.selected_defaults.transport } }]
          : []),
        { label: "Hotel", selection: tripSelections.hotel || { intent: "hotel", option: tripPlan.selected_defaults.hotel }, nights: tripPlan.details.nights },
        ...(!tripPlan.details.one_way && tripPlan.route_legs.some((leg) => leg.direction === "return" && leg.bookable)
          ? [{ label: "Return travel", selection: tripSelections.trip_return || { intent: tripPlan.selected_defaults.return.intent, option: tripPlan.selected_defaults.return } }]
          : []),
      ]
      : [
        { label: "Event ticket", selection: tripSelections.event },
        { label: "Outbound travel", selection: tripSelections.outbound },
        { label: "Hotel", selection: tripSelections.hotel },
        { label: "Return travel", selection: tripSelections.return },
      ];
    if (selectedItems.some(({ selection }) => !selection?.option)) {
      toast.error("Select an event ticket, outbound travel, hotel, and return travel first.");
      return;
    }
    setLoading(true);
    try {
      const payloads = selectedItems.map(({ selection, nights: itemNights }) => ({
        intent: selection.intent,
        option_id: selection.option.id,
        quantity: travelers,
        nights: itemNights || 1,
        rooms: selection.intent === "hotel" ? rooms : 1,
      }));
      const pricing = await confirmPlanBooking(payloads);
      const items = pricing.items.map((item, index) => ({
        ...item,
        label: selectedItems[index].label,
      }));
      setEventCheckout({ items, preview: pricing, promoCode: "", insurance: false });
      setEventPlanStatus("idle");
      setEventPlanError("");
    } catch (error) {
      toast.error(`Could not calculate plan pricing: ${formatApiError(error)}`);
    } finally {
      setLoading(false);
    }
  };

  const refreshEventPricing = async (promoCode, insurance) => {
    if (!eventCheckout) return;
    try {
      const pricing = await confirmPlanBooking(eventCheckout.items.map((item) => ({
        intent: item.intent,
        option_id: item.option.id,
        quantity: item.quantity,
        nights: item.nights,
        rooms: item.rooms,
        promo_code: promoCode,
        insurance,
      })));
      const items = pricing.items.map((item, index) => ({
        ...item,
        label: eventCheckout.items[index].label,
      }));
      setEventCheckout({ items, preview: pricing, promoCode, insurance });
    } catch (error) {
      toast.error(`Could not update plan pricing: ${formatApiError(error)}`);
    }
  };

  const bookEventPlan = async (checkout = {}) => {
    if (!chatResp?.run_id || !tripPlan || loading) return;
    if (!approved) {
      setLoading(true);
      setEventPlanStatus("processing");
      setEventPlanError("");
      try {
        await approvePlan(chatResp.run_id, userId);
        for (let index = 0; index < chatResp.steps.length; index += 1) {
          const step = chatResp.steps[index];
          setPlan((current) => current.map((item, itemIndex) => (
            itemIndex === index ? { ...item, status: "in-progress" } : item
          )));
          try {
            const completed = await executeStep(chatResp.run_id, index, userId);
            setResults((current) => [...current, { index, tool: completed.tool, result: completed.result }]);
            setPlan((current) => current.map((item, itemIndex) => (
              itemIndex === index ? { ...item, status: "done", result: completed.result } : item
            )));
          } catch (error) {
            setPlan((current) => current.map((item, itemIndex) => (
              itemIndex === index ? { ...item, status: "failed" } : item
            )));
            throw new Error(`${toolLabel(step.tool)} search failed: ${formatApiError(error)}`);
          }
        }
        setApproved(true);
        setEventPlanStatus("ready");
        toast.success("Plan approved and searches completed. Review payment to confirm bookings.");
      } catch (error) {
        const message = formatApiError(error);
        setEventPlanError(message);
        setEventPlanStatus("failed");
        toast.error(message);
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!eventCheckout) return;
    setLoading(true);
    setEventPlanStatus("processing");
    setEventPlanError("");
    try {
      for (const item of eventCheckout.items) {
        try {
          const booking = await createBooking({
            intent: item.intent,
            option_id: item.option.id,
            user_id: userId,
            run_id: chatResp.run_id,
            quantity: item.quantity,
            nights: item.nights,
            rooms: item.rooms,
            confirmed: true,
            user_request: chatResp.request,
            passengers: checkout.passengers,
            contact: checkout.contact,
            promo_code: checkout.promo_code,
            insurance: checkout.insurance,
            payment_method: checkout.payment_method,
          });
          setEventBookings((current) => [...current, booking]);
        } catch (error) {
          throw new Error(`${item.label} booking failed: ${formatApiError(error)}`);
        }
      }
      setEventPlanStatus("done");
      await refreshHistory();
      toast.success("Plan booked. Each simulated booking is saved to History.");
    } catch (error) {
      const message = formatApiError(error);
      setEventPlanError(message);
      setEventPlanStatus("failed");
      toast.error(message);
      await refreshHistory();
    } finally {
      setLoading(false);
    }
  };

  const startVoiceInput = () => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setSpeechSupported(false);
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => {
      setListening(false);
      toast.error("Voice input could not be captured. Please try typing.");
    };
    recognition.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript;
      if (transcript) {
        if (experience === "chat") setConversationInput(transcript);
        else setGoal(transcript);
      }
    };
    recognition.start();
  };

  const renderResult = ({ index, tool, result }) => (
    <Card key={`${tool}-${index}`} className="p-4 bg-white border-slate-200">
      <div className="flex items-center gap-2 mb-3">
        <Badge className={`${TOOL_COLOR[tool] || TOOL_COLOR.unknown} border capitalize`}>{toolLabel(tool)}</Badge>
        <span className="text-xs text-slate-500">Simulated output</span>
      </div>
      {result.results?.length ? (
        <div className="space-y-2">
          {result.tradeoff && <p className="text-xs text-slate-600">{result.tradeoff}</p>}
          {result.results.map((item, index) => {
            const title = item.name || item.hotel || item.cinema || item.movie || item.airline
              || item.train_name || item.operator || item.match || item.event || `Option ${index + 1}`;
            const price = item.price ?? item.price_per_night;
            return (
              <div key={`${title}-${index}`} className="rounded-lg bg-slate-50 p-3 text-sm">
                <div className="flex justify-between gap-3">
                  <span className="font-medium text-slate-800">
                    {title}
                    {item.recommended && <Badge className="ml-2 bg-indigo-100 text-indigo-800 border border-indigo-200">Recommended</Badge>}
                  </span>
                  {price != null && <span className="font-semibold text-slate-700">₹{price}</span>}
                </div>
                {item.reason && <p className="text-xs text-indigo-700 mt-1">{item.reason}</p>}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-sm text-slate-700">
          {result.budget != null && <p>Budget: ₹{result.budget}</p>}
          {result.allocation && <p className="mt-1">Allocation: {JSON.stringify(result.allocation)}</p>}
          {result.itinerary?.map((item) => (
            <p key={`${item.day}-${item.activity}`} className="mt-1">{item.activity}</p>
          ))}
          {!result.budget && !result.allocation && !result.itinerary && <p>Step completed.</p>}
        </div>
      )}
    </Card>
  );

  return (
    <div className="min-h-screen w-full overflow-x-hidden">
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
          <div className="flex items-center gap-2 sm:gap-4">
            {authEnabled && <span className="max-w-[92px] truncate text-xs sm:max-w-none sm:text-sm font-medium text-slate-700">{user.name}</span>}
            <Badge variant="outline" className="hidden md:inline-flex border-amber-300 bg-amber-50 text-amber-800">
              <Info className="w-3 h-3 mr-1" /> Demo — all tools are simulated
            </Badge>
            {authEnabled && (
              <Button variant="outline" size="sm" onClick={onLogout} aria-label="Log out">
                <LogOut className="w-4 h-4 sm:mr-1.5" /><span className="hidden sm:inline">Logout</span>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <Tabs value={tab} onValueChange={setTab} className="w-full">
          <TabsList className="mb-6" data-testid="main-tabs">
            <TabsTrigger value="agent" data-testid="tab-agent"><Zap className="w-4 h-4 mr-1.5" />Agent</TabsTrigger>
            <TabsTrigger value="history" data-testid="past-bookings-tab" onClick={refreshHistory}>
              <History className="w-4 h-4 mr-1.5" />History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="agent">
            <div className="flex gap-2 mb-5">
              <Button
                variant={experience === "chat" ? "default" : "outline"}
                onClick={() => setExperience("chat")}
                className={experience === "chat" ? "bg-indigo-600 hover:bg-indigo-700 text-white" : ""}
              >
                Conversational chat
              </Button>
              <Button
                variant={experience === "agent" ? "default" : "outline"}
                onClick={() => setExperience("agent")}
                className={experience === "agent" ? "bg-indigo-600 hover:bg-indigo-700 text-white" : ""}
              >
                Tool runner
              </Button>
            </div>
            {experience === "chat" ? (
              <ConversationPanel
                messages={conversation}
                user={user}
                input={conversationInput}
                onInputChange={setConversationInput}
                onSend={(message) => sendConversation(message)}
                onReset={resetConversation}
                loading={loading}
                speechSupported={speechSupported}
                listening={listening}
                onVoiceInput={startVoiceInput}
                tripPlan={tripPlan}
                approved={approved}
                selections={tripSelections}
                onSelectOption={selectOption}
                selection={selected && selectedIntent ? { intent: selectedIntent, option: selected } : null}
                preview={preview}
                quantity={quantity}
                nights={nights}
                rooms={rooms}
                onRoomsChange={(value) => {
                  setRooms(value);
                  refreshPreview(quantity, nights, value);
                }}
                onPricingChange={(promoCode, insurance) => refreshPreview(quantity, nights, rooms, promoCode, insurance)}
                onQuantityChange={(value) => {
                  setQuantity(value);
                  refreshPreview(value, nights);
                }}
                onNightsChange={(value) => {
                  setNights(value);
                  refreshPreview(quantity, value);
                }}
                onConfirm={confirmMockBooking}
                onCancelSelection={() => {
                  setSelected(null);
                  setSelectedIntent(null);
                  setPreview(null);
                  setReceipt(null);
                }}
                receipt={receipt}
                onNextBooking={() => {
                  setSelected(null);
                  setSelectedIntent(null);
                  setPreview(null);
                  setReceipt(null);
                }}
                onEventOptionSelect={selectEventOption}
                onTripOptionSelect={selectTripOption}
                onBookEventPlan={bookEventPlan}
                eventCheckout={eventCheckout}
                onOpenEventCheckout={openEventCheckout}
                onEventPricingChange={refreshEventPricing}
                onCancelEventCheckout={() => {
                  setEventCheckout(null);
                  setEventPlanStatus("idle");
                }}
                eventBookings={eventBookings}
                eventPlanStatus={eventPlanStatus}
                eventPlanError={eventPlanError}
              />
            ) : (
              <>
            <section className="mb-6">
              <h2 className="font-heading text-2xl sm:text-3xl md:text-4xl font-extrabold text-slate-900 mb-2">
                Tell AURA your plan.
              </h2>
              {hubTool && (
                <p className="text-sm text-indigo-700 mb-3">Feature selected: {toolLabel(hubTool)}</p>
              )}
              <div className="mt-5 flex flex-col sm:flex-row gap-2">
                <div className="flex flex-1 gap-2">
                  <Input
                    value={goal}
                    onChange={(event) => setGoal(event.target.value)}
                    onKeyDown={(event) => event.key === "Enter" && submitGoal()}
                    placeholder={pendingRequest ? "Answer AURA's follow-up question" : "e.g. Plan a Goa trip with a budget, flight and hotel"}
                    className="h-12 text-sm sm:text-base"
                    data-testid="goal-input"
                  />
                  {speechSupported && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={startVoiceInput}
                      disabled={loading || listening}
                      aria-label={listening ? "Listening" : "Use voice input"}
                      className="h-12 w-12 shrink-0"
                      data-testid="voice-input-btn"
                    >
                      {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </Button>
                  )}
                </div>
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
              {!speechSupported && (
                <p className="text-[11px] text-slate-500 mt-2">Voice input is not supported in this browser.</p>
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="text-xs text-slate-500 self-center mr-1">Quick demos:</span>
                {PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => { setGoal(preset.text); submitGoal(preset.text, preset.tool); }}
                    className="text-sm px-4 py-2 rounded-full border border-slate-200 bg-white hover:border-indigo-400 hover:text-indigo-700 transition-colors whitespace-nowrap"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </section>

            {chatResp && (
              <section ref={resultsRef} className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <aside className="lg:col-span-4">
                  <Card className="p-4 bg-white border-slate-200">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-heading font-bold text-slate-900">Execution Timeline</h3>
                      <Badge className={`${TOOL_COLOR[intent] || TOOL_COLOR.unknown} border capitalize`}>
                        <IntentIcon className="w-3 h-3 mr-1" />{toolLabel(intent)}
                      </Badge>
                    </div>
                    <Timeline steps={plan} />
                  </Card>
                </aside>

                <section className="lg:col-span-8 space-y-5">
                  <ParametersCard intent={intent} params={chatResp.params || {}} missing={chatResp.missing || []} />
                  {chatResp.missing?.length > 0 && (
                    <Card className="p-4 border-amber-200 bg-amber-50 text-sm text-amber-900">
                      {chatResp.question || chatResp.missing[0]}
                    </Card>
                  )}
                  {!chatResp.missing?.length && !approved && (
                    <Card className="p-5 border-indigo-200 bg-indigo-50/50">
                      <h3 className="font-heading font-bold text-slate-900">Review your plan</h3>
                      <ol className="list-decimal pl-5 mt-2 space-y-1 text-sm text-slate-700">
                        {(chatResp.steps || []).map((step, index) => (
                          <li key={`${step.tool}-${index}`}>
                            <span className="font-semibold capitalize">{toolLabel(step.tool)}</span>
                            <span className="text-slate-500"> — {JSON.stringify(step.parameters)}</span>
                          </li>
                        ))}
                      </ol>
                      <p className="text-xs text-slate-600 mt-3">Only simulated tools will run. No real bookings or payments are made.</p>
                      <Button
                        onClick={approveAndRun}
                        disabled={loading}
                        className="mt-4 bg-indigo-600 hover:bg-indigo-700 text-white"
                        data-testid="approve-run-btn"
                      >
                        {loading ? <RefreshCw className="w-4 h-4 animate-spin mr-1.5" /> : <Zap className="w-4 h-4 mr-1.5" />}
                        Approve &amp; Run
                      </Button>
                    </Card>
                  )}
                  {results.filter(({ tool }) => !BOOKING_TOOLS.includes(tool)).map(renderResult)}
                  {(options.length > 0 || results.some(({ tool }) => BOOKING_TOOLS.includes(tool))) && !receipt && (
                    <OptionList
                      intent={intent}
                      options={options}
                      selectedId={selected?.id}
                      onSelect={selectOption}
                    />
                  )}
                  {!receipt && selected && preview && intent === "movie" && (
                    <SeatPicker
                      option={selected}
                      requiredCount={Number(quantity) || 1}
                      selectedSeats={selectedSeats}
                      onSelectedSeatsChange={setSelectedSeats}
                      onBack={() => {
                        setSelected(null);
                        setPreview(null);
                        updateBookingStep("Select mock option", "in-progress");
                      }}
                    />
                  )}
                  {!receipt && selected && preview && (
                    <ConfirmationCard
                      intent={intent}
                      option={selected}
                      quantity={quantity}
                      nights={nights}
                      rooms={rooms}
                      onRoomsChange={(value) => {
                        setRooms(value);
                        if (tripPlan?.kind !== "destination_trip") refreshPreview(quantity, nights, value);
                      }}
                      preview={preview}
                      seats={selectedSeats}
                      user={user}
                      requiresApproval={chatResp?.mode === "conversation"}
                      approved={approved}
                      onPricingChange={(promoCode, insurance) => refreshPreview(quantity, nights, rooms, promoCode, insurance)}
                      onQuantityChange={(value) => {
                        setQuantity(value);
                        refreshPreview(value, nights);
                      }}
                      onNightsChange={(value) => {
                        setNights(value);
                        refreshPreview(quantity, value);
                      }}
                      onConfirm={confirmMockBooking}
                      onCancel={() => {
                        setSelected(null);
                        setPreview(null);
                        updateBookingStep("Select mock option", "in-progress");
                      }}
                    />
                  )}
                  {receipt && <BookingReceipt receipt={receipt} onNew={() => {
                    resetFlow();
                    setGoal("");
                  }} />}
                </section>
              </section>
            )}

            {!chatResp && (
              <section className="mt-12 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {PRESETS.map((preset) => {
                  const Icon = TOOL_ICON[preset.tool] || Sparkles;
                  return (
                    <Card
                      key={preset.label}
                      className="min-h-44 p-6 bg-white hover:border-indigo-400 hover:shadow-md transition-all cursor-pointer"
                      onClick={() => { setGoal(preset.text); submitGoal(preset.text, preset.tool); }}
                    >
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${TOOL_COLOR[preset.tool]}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <h4 className="font-heading font-bold text-slate-900 text-lg mb-1">{preset.title}</h4>
                      <p className="text-sm text-slate-500 leading-relaxed">{preset.text}</p>
                    </Card>
                  );
                })}
              </section>
            )}
              </>
            )}
          </TabsContent>

          <TabsContent value="history">
            <HistoryList
              bookings={history.bookings}
              runs={history.runs}
              onRefresh={refreshHistory}
            />
          </TabsContent>
        </Tabs>

        <footer className="mt-16 py-6 border-t border-slate-200 text-center text-xs text-slate-500">
          AURA · a college project by B.Tech students · All tools are simulated.
        </footer>
      </main>
    </div>
  );
}
