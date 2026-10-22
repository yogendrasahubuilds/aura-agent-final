import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const AUTH_ENABLED = (process.env.REACT_APP_AUTH_ENABLED || "true").trim().toLowerCase() !== "false";

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const AUTH_TOKEN_KEY = "aura-access-token";
export const saveAuth = (data) => {
  window.localStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
  window.localStorage.setItem("aura-user-id", data.user.id);
};
export const clearAuth = () => {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem("aura-user-id");
};

api.interceptors.request.use((config) => {
  if (!AUTH_ENABLED) return config;
  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const path = error.config?.url || "";
    if (error.response?.status === 401 && !path.includes("/auth/login") && !path.includes("/auth/signup")) {
      clearAuth();
      window.dispatchEvent(new Event("aura:unauthorized"));
    }
    return Promise.reject(error);
  },
);

export const getUserId = () => {
  return window.localStorage.getItem("aura-user-id");
};

export const formatApiError = (error) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === "string") return item;
      if (!item || typeof item !== "object") return String(item);
      const location = Array.isArray(item.loc)
        ? item.loc.filter((part) => !["body", "query", "path"].includes(part)).join(".")
        : "";
      const message = typeof item.msg === "string" ? item.msg : "";
      return [location, message].filter(Boolean).join(": ") || JSON.stringify(item);
    }).join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return error?.message || "The request could not be completed.";
};

export const signup = (name, email, password) =>
  api.post("/auth/signup", { name, email, password }).then((r) => r.data);
export const login = (email, password) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);
export const getCurrentUser = () => api.get("/auth/me").then((r) => r.data);
export const chat = (message, userId, tool) =>
  api.post("/chat", { message, user_id: userId, tool }).then((r) => r.data);
export const conversationalChat = (message, userId, conversation, reset = false, signal) =>
  api.post("/chat", {
    message,
    user_id: userId,
    mode: "conversation",
    conversation,
    reset,
  }, { signal }).then((r) => r.data);
export const approvePlan = (runId, userId) =>
  api.post(`/runs/${runId}/approve`, { user_id: userId }).then((r) => r.data);
export const executeStep = (runId, index, userId) =>
  api.post(`/runs/${runId}/steps`, { index, user_id: userId }).then((r) => r.data);
export const searchOptions = (intent, params) =>
  api.post("/search", { intent, params }).then((r) => r.data);
export const confirmBooking = (payload) => api.post("/confirm", payload).then((r) => r.data);
export const confirmPlanBooking = (items) => api.post("/confirm/plan", { items }).then((r) => r.data);
export const createBooking = (payload) => api.post("/book", payload).then((r) => r.data);
export const listBookings = (userId) =>
  api.get("/bookings", { params: userId ? { user_id: userId } : {} }).then((r) => r.data);
export const getHistory = (userId) => api.get(`/history/${userId}`).then((r) => r.data);
