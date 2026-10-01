import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api";
import { useAuth } from "../auth";
import ThemeToggle from "../components/ThemeToggle";
import { btnPrimary, inputClass } from "../ui";

export default function LoginPage() {
  const { user, setupRequired, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (setupRequired) {
    return <Navigate to="/setup" replace />;
  }
  if (user) {
    return <Navigate to="/sessions" replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/sessions", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-bg">
      <header className="relative z-10 flex justify-end px-6 py-4">
        <ThemeToggle />
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-6 pb-16">
        <div className="w-full max-w-[400px]">
          <div className="flex flex-col items-center text-center">
            <span aria-hidden="true" className="h-5 w-5 rounded-pill bg-ink" />
            <h1 className="mt-4 text-4xl font-medium tracking-[-0.02em]">RAG</h1>
            <p className="mt-2 max-w-xs text-sm text-muted">
              Ask your own documents anything. Every answer keeps its sources.
            </p>
          </div>

          <form className="mt-8" onSubmit={onSubmit}>
            <div className="flex flex-col gap-4">
              <label className="flex flex-col gap-2 text-sm font-medium text-muted">
                Username
                <input
                  className={inputClass}
                  autoFocus
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-medium text-muted">
                Password
                <input
                  className={inputClass}
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
            </div>

            {error ? (
              <p role="alert" className="mt-4 rounded-control bg-panel px-3 py-2 text-sm text-ink">
                {error}
              </p>
            ) : null}

            <button className={`${btnPrimary} mt-6 w-full`} type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
