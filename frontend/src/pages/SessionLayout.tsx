import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type MessageSearchResult, type Session } from "../api";
import { useAuth } from "../auth";
import CommandPalette from "../components/CommandPalette";
import ThemeToggle from "../components/ThemeToggle";
import { btnGhost, btnSecondary } from "../ui";

const SIDEBAR_KEY = "cwd:sidebar";

// A recognizable sidebar/panel glyph: the frame plus a shaded left pane, with a
// chevron giving the direction the toggle will move it.
function SidebarIcon({
  collapsed = false,
  className = "h-4 w-4",
}: {
  collapsed?: boolean;
  className?: string;
}) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="3" y="4" width="18" height="16" />
      <path d="M9 4v16" />
      <rect x="3" y="4" width="6" height="16" fill="currentColor" stroke="none" opacity="0.22" />
      <path d={collapsed ? "M12.5 9.5l3 2.5-3 2.5" : "M15.5 9.5l-3 2.5 3 2.5"} />
    </svg>
  );
}

export default function SessionLayout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, logout } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) !== "closed";
    } catch {
      return true;
    }
  });
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_KEY, sidebarOpen ? "open" : "closed");
    } catch {
      // Storage can be unavailable; the layout still works for this session.
    }
  }, [sidebarOpen]);

  const sessionsQuery = useQuery({
    queryKey: ["sessions"],
    queryFn: api.listSessions,
  });

  const createSession = useMutation({
    mutationFn: () => api.createSession(),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      navigate(`/sessions/${session.id}`);
    },
  });

  async function onLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const mod = event.metaKey || event.ctrlKey;
      if (mod && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((open) => !open);
      } else if (mod && event.key.toLowerCase() === "b") {
        event.preventDefault();
        setSidebarOpen((open) => !open);
      } else if (event.key === "/" && !mod) {
        const active = document.activeElement;
        const typing =
          active instanceof HTMLInputElement ||
          active instanceof HTMLTextAreaElement ||
          (active instanceof HTMLElement && active.isContentEditable);
        if (!typing) {
          event.preventDefault();
          window.dispatchEvent(new Event("cwd:focus-composer"));
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function openSession(session: Session) {
    navigate(`/sessions/${session.id}`);
  }

  function openMessage(result: MessageSearchResult) {
    navigate(`/sessions/${result.session_id}?m=${result.message_id}`);
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg text-ink">
      {sidebarOpen ? (
        <aside className="flex w-72 shrink-0 flex-col border-r border-line bg-panel">
          <div className="border-b border-line px-4 py-4">
            <div className="flex items-center gap-2.5">
              <span aria-hidden="true" className="h-2.5 w-2.5 shrink-0 bg-accent" />
              <span className="font-display text-xl font-medium tracking-tight">RAG</span>
              <span className="ml-auto truncate font-mono text-[11px] text-faint">
                {user?.username}
              </span>
              <button
                type="button"
                className="flex h-8 w-8 shrink-0 items-center justify-center border border-line text-ink transition-colors duration-150 hover:border-accent hover:text-accent"
                onClick={() => setSidebarOpen(false)}
                aria-label="Hide sidebar"
                title="Hide sidebar"
              >
                <SidebarIcon />
              </button>
            </div>
            <p className="mt-2 font-reading text-xs italic text-muted">
              A reading room for your documents.
            </p>
          </div>

          <div className="flex gap-2 px-4 py-3">
            <button
              className={`${btnSecondary} flex-1`}
              onClick={() => setPaletteOpen(true)}
              title="Search (Ctrl/⌘K)"
            >
              Search
            </button>
            <button
              className={`${btnSecondary} flex-1`}
              onClick={() => createSession.mutate()}
              disabled={createSession.isPending}
            >
              + New
            </button>
          </div>

          <nav
            aria-label="Sessions"
            className="min-h-0 flex-1 overflow-y-auto border-t border-line"
          >
            {sessionsQuery.isLoading ? (
              <div aria-busy="true" className="space-y-px p-2">
                <div className="skeleton h-10 w-full" />
                <div className="skeleton h-10 w-full" />
                <div className="skeleton h-10 w-3/4" />
              </div>
            ) : null}
            {sessionsQuery.isError ? (
              <p role="alert" className="px-4 py-3 font-reading text-xs text-danger">
                Could not load sessions.
              </p>
            ) : null}
            {sessionsQuery.data?.length === 0 ? (
              <p className="px-4 py-3 font-reading text-sm italic text-muted">No sessions yet.</p>
            ) : null}
            {sessionsQuery.data?.map((session: Session) => (
              <NavLink
                key={session.id}
                to={`/sessions/${session.id}`}
                className={({ isActive }) =>
                  `flex items-baseline gap-3 border-l-2 px-4 py-3 no-underline transition-colors duration-150 ${
                    isActive
                      ? "border-accent bg-panel2"
                      : "border-transparent hover:border-line hover:bg-panel2/50"
                  }`
                }
              >
                <span
                  className={`min-w-0 flex-1 truncate font-reading text-sm ${
                    session.title ? "" : "italic"
                  }`}
                >
                  {session.title}
                </span>
                <span className="shrink-0 font-mono text-[11px] tabular-nums text-faint">
                  {session.document_count}
                </span>
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-line p-2">
            <ThemeToggle className="w-full justify-start" />
            <button className={`${btnGhost} w-full justify-start`} onClick={onLogout}>
              Log out
            </button>
          </div>
        </aside>
      ) : (
        <button
          type="button"
          className="fixed left-0 top-1/2 z-30 flex -translate-y-1/2 items-center gap-2 border border-l-0 border-line bg-panel px-2.5 py-3 text-ink shadow-[0_8px_24px_-8px_rgba(12,18,28,0.45)] transition-colors duration-150 hover:border-accent hover:text-accent"
          onClick={() => setSidebarOpen(true)}
          aria-label="Show sidebar"
          title="Show sidebar"
        >
          <SidebarIcon collapsed className="h-5 w-5" />
        </button>
      )}

      <main className="min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </main>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        sessions={sessionsQuery.data ?? []}
        onOpenSession={openSession}
        onOpenMessage={openMessage}
      />
    </div>
  );
}
