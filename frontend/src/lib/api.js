import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const chat = (message) => api.post("/chat", { message }).then((r) => r.data);
export const searchOptions = (intent, params) =>
  api.post("/search", { intent, params }).then((r) => r.data);
export const confirmBooking = (payload) => api.post("/confirm", payload).then((r) => r.data);
export const createBooking = (payload) => api.post("/book", payload).then((r) => r.data);
export const listBookings = () => api.get("/bookings").then((r) => r.data);
