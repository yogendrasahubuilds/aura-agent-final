import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatApiError, login, saveAuth, signup } from "@/lib/api";

export default function AuthPage({ mode, onAuthenticated }) {
  const isSignup = mode === "signup";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const data = isSignup
        ? await signup(name, email, password)
        : await login(email, password);
      saveAuth(data);
      onAuthenticated(data.user);
    } catch (requestError) {
      setError(formatApiError(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-md p-7 bg-white border-slate-200 shadow-lg">
        <div className="flex items-center gap-3 mb-7">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-600 to-cyan-500 flex items-center justify-center text-white">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-heading text-2xl font-extrabold text-slate-900">AURA</h1>
            <p className="text-xs text-slate-500">Autonomous Universal Resource Agent</p>
          </div>
        </div>
        <h2 className="font-heading text-xl font-bold text-slate-900">
          {isSignup ? "Create your account" : "Welcome back"}
        </h2>
        <p className="text-sm text-slate-500 mt-1 mb-5">
          {isSignup ? "Sign up to save your plans and bookings." : "Log in to continue to your plans and bookings."}
        </p>
        <form onSubmit={submit} className="space-y-4">
          {isSignup && (
            <div className="space-y-1.5">
              <Label htmlFor="auth-name">Name</Label>
              <Input id="auth-name" value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" required maxLength={100} />
            </div>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="auth-email">Email</Label>
            <Input id="auth-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="auth-password">Password</Label>
            <Input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete={isSignup ? "new-password" : "current-password"}
              minLength={isSignup ? 6 : 1}
              required
            />
            {isSignup && <p className="text-xs text-slate-500">At least 6 characters.</p>}
          </div>
          {error && <p role="alert" className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md p-3">{error}</p>}
          <Button type="submit" disabled={submitting} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">
            {submitting ? "Please wait…" : isSignup ? "Create account" : "Log in"}
          </Button>
        </form>
        <p className="text-sm text-center text-slate-600 mt-5">
          {isSignup ? "Already have an account? " : "New to AURA? "}
          <Link className="font-semibold text-indigo-700 hover:underline" to={isSignup ? "/login" : "/signup"}>
            {isSignup ? "Log in" : "Sign up"}
          </Link>
        </p>
      </Card>
    </main>
  );
}
