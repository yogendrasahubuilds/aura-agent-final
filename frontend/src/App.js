import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import AuraApp from "@/pages/AuraApp";
import AuthPage from "@/pages/AuthPage";
import { AUTH_ENABLED, clearAuth, getCurrentUser } from "@/lib/api";
import { useEffect, useState } from "react";

const GUEST_USER = { id: "default-user", name: "Guest", email: "guest@local" };

function AppRoutes() {
  const [auth, setAuth] = useState(() => (
    AUTH_ENABLED
      ? { loading: true, user: null }
      : { loading: false, user: GUEST_USER }
  ));

  useEffect(() => {
    if (!AUTH_ENABLED) return undefined;
    let active = true;
    const token = window.localStorage.getItem("aura-access-token");
    if (!token) {
      setAuth({ loading: false, user: null });
      return undefined;
    }
    getCurrentUser()
      .then((user) => {
        if (active) setAuth({ loading: false, user });
      })
      .catch(() => {
        clearAuth();
        if (active) setAuth({ loading: false, user: null });
      });
    const invalidate = () => setAuth({ loading: false, user: null });
    window.addEventListener("aura:unauthorized", invalidate);
    return () => {
      active = false;
      window.removeEventListener("aura:unauthorized", invalidate);
    };
  }, []);

  if (!AUTH_ENABLED) {
    return <Routes><Route path="*" element={<AuraApp key="default-user" user={GUEST_USER} authEnabled={false} />} /></Routes>;
  }
  if (auth.loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading AURA…</div>;
  }
  if (!auth.user) {
    return (
      <Routes>
        <Route path="/signup" element={<AuthPage mode="signup" onAuthenticated={(user) => setAuth({ loading: false, user })} />} />
        <Route path="*" element={<AuthPage mode="login" onAuthenticated={(user) => setAuth({ loading: false, user })} />} />
      </Routes>
    );
  }
  const logout = () => {
    clearAuth();
    setAuth({ loading: false, user: null });
  };
  return (
    <Routes>
      <Route path="*" element={<AuraApp key={auth.user.id} user={auth.user} authEnabled onLogout={logout} />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App min-h-screen">
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </div>
  );
}

export default App;
