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
    <div className="relative min-h-screen overflow-hidden bg-bg">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 80% at 12% -10%, rgb(var(--c-accent) / 0.08), transparent 58%)",
        }}
      />

      <div className="absolute right-4 top-4 z-10">
        <ThemeToggle />
      </div>

      <div className="relative mx-auto grid min-h-screen max-w-5xl items-center gap-14 px-6 py-16 lg:grid-cols-[1.1fr_minmax(320px,400px)] lg:gap-20">
        <div className="animate-settle">
          <p className="flex items-center gap-3 font-mono text-[11px] tracking-wide text-muted">
            <span aria-hidden="true" className="h-2 w-2 bg-accent" />
            private · one reader
          </p>

          <h1 className="mt-8 font-display text-6xl font-medium leading-[0.95] tracking-tight text-ink sm:text-7xl">
            RAG
          </h1>

          <p className="mt-6 max-w-md font-reading text-xl leading-relaxed text-ink/90">
            Ask your own documents anything. Every answer keeps its receipts.
          </p>

          <figure className="mt-12 max-w-md border-l border-accent/50 pl-5">
            <blockquote className="font-reading text-lg italic leading-relaxed text-ink/85">
              Migration to the new registry began in the spring of 1968.
            </blockquote>
            <figcaption className="mt-3 flex items-baseline gap-2 font-mono text-[11px] text-faint">
              <span className="text-accent">[1]</span>
              <span>Report_on_Archives.pdf · p. 12</span>
            </figcaption>
          </figure>
        </div>

        <form
          className="animate-settle border border-line bg-panel p-8"
          onSubmit={onSubmit}
        >
          <h2 className="font-display text-2xl font-medium text-ink">Sign in</h2>
          <p className="mt-1 font-reading text-sm text-muted">Enter the reading room.</p>

          <div className="mt-7 flex flex-col gap-5">
            <label className="flex flex-col gap-2 font-mono text-[11px] tracking-wide text-muted">
              Username
              <input
                className={inputClass}
                autoFocus
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>

            <label className="flex flex-col gap-2 font-mono text-[11px] tracking-wide text-muted">
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
            <p
              role="alert"
              className="mt-5 border-l-2 border-danger bg-danger/5 px-3 py-2 font-reading text-sm text-danger"
            >
              {error}
            </p>
          ) : null}

          <button className={`${btnPrimary} mt-7 w-full`} type="submit" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
