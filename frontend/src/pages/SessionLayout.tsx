import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type MessageSearchResult, type Session } from "../api";
import { useAuth } from "../auth";
import CommandPalette from "../components/CommandPalette";
import { ConfirmDialog, Dialog } from "../components/Dialog";
import DropZone from "../components/DropZone";
import { SpinnerIcon } from "../components/icons";
import ThemeToggle from "../components/ThemeToggle";
import { btnDanger, btnGhost, btnPrimary, btnSecondary } from "../ui";

const SIDEBAR_KEY = "cwd:sidebar";

const iconBtn =
  "inline-grid h-9 w-9 shrink-0 place-items-center rounded-pill text-muted transition-colors duration-150 hover:bg-panel2 hover:text-ink";

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
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <rect x="3" y="4" width="18" height="16" rx="3" />
      <path d="M9 4v16" />
      <path d={collapsed ? "M13 9.5l3 2.5-3 2.5" : "M16 9.5l-3 2.5 3 2.5"} />
    </svg>
  );
}

function CheckIcon({ className = "h-3 w-3" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 12l5 5 9-10" />
    </svg>
  );
}

function ChecklistIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M10 6h11M10 12h11M10 18h11" />
      <path d="M4 6l1.5 1.5L8 5M4 12l1.5 1.5L8 11M4 18l1.5 1.5L8 17" />
    </svg>
  );
}

export default function SessionLayout() {
  const navigate = useNavigate();
  const location = useLocation();
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
  const [manageOpen, setManageOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmDelete, setConfirmDelete] = useState(false);

  const currentSessionId = location.pathname.match(/^\/sessions\/([^/]+)/)?.[1];

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

  const sessions = sessionsQuery.data ?? [];
  const allSelected = sessions.length > 0 && selected.size === sessions.length;

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected(allSelected ? new Set() : new Set(sessions.map((s) => s.id)));
  }

  function closeManage() {
    setManageOpen(false);
    setSelected(new Set());
  }

  const deleteSelected = useMutation({
    mutationFn: (ids: string[]) => api.deleteSessions(ids),
    onSuccess: (_result, ids) => {
      queryClient.setQueryData(["sessions"], (old: unknown) =>
        Array.isArray(old)
          ? old.filter((session) => !ids.includes((session as Session).id))
          : old
      );
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      if (currentSessionId && ids.includes(currentSessionId)) {
        localStorage.removeItem("cwd:last");
        navigate("/sessions", { replace: true });
      }
      closeManage();
    },
    onSettled: () => setConfirmDelete(false),
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

  function onDropFiles(files: File[]) {
    window.dispatchEvent(new CustomEvent("cwd:drop-files", { detail: files }));
  }

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-bg text-ink">
      {sidebarOpen ? (
        <aside className="relative z-10 flex w-72 shrink-0 flex-col border-r border-line bg-bg">
          <div className="px-4 py-4">
            <div className="flex items-center gap-2.5">
              <span aria-hidden="true" className="h-3.5 w-3.5 shrink-0 rounded-pill bg-ink" />
              <span className="text-xl font-medium tracking-[-0.02em]">RAG</span>
              <span className="ml-auto truncate text-sm text-muted">{user?.username}</span>
              <button
                type="button"
                className={iconBtn}
                onClick={() => setSidebarOpen(false)}
                aria-label="Hide sidebar"
                title="Hide sidebar"
              >
                <SidebarIcon />
              </button>
            </div>
            <p className="mt-2 pl-6 text-sm text-muted">A reading room for your documents.</p>
          </div>

          <div className="flex gap-2 px-4 pb-3">
            <button
              className={`${btnSecondary} flex-1`}
              onClick={() => setPaletteOpen(true)}
              title="Search (Ctrl/⌘K)"
            >
              Search
            </button>
            <button
              className={`${btnPrimary} flex-1`}
              onClick={() => createSession.mutate()}
              disabled={createSession.isPending}
            >
              New
            </button>
          </div>

          {manageOpen ? (
            <div className="mx-3 mb-2 flex items-center gap-1 rounded-control bg-panel2 px-2 py-1.5">
              <button className={btnGhost} onClick={toggleAll}>
                {allSelected ? "Clear" : "Select all"}
              </button>
              <span className="ml-auto text-sm tabular-nums text-muted">
                {selected.size} selected
              </span>
              <button
                className={btnDanger}
                onClick={() => setConfirmDelete(true)}
                disabled={selected.size === 0}
              >
                Delete
              </button>
              <button className={btnGhost} onClick={closeManage}>
                Done
              </button>
            </div>
          ) : (
            <div className="px-4 pb-3">
              <button
                className={`${btnSecondary} w-full justify-between`}
                onClick={() => setManageOpen(true)}
                title="Select several sessions to delete"
              >
                <span className="inline-flex items-center gap-2">
                  <ChecklistIcon />
                  Manage sessions
                </span>
                <span className="text-sm tabular-nums text-muted">{sessions.length}</span>
              </button>
            </div>
          )}

          <nav aria-label="Sessions" className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
            {sessionsQuery.isLoading ? (
              <div aria-busy="true" className="space-y-1">
                <div className="skeleton h-11 w-full" />
                <div className="skeleton h-11 w-full" />
                <div className="skeleton h-11 w-3/4" />
              </div>
            ) : null}
            {sessionsQuery.isError ? (
              <p role="alert" className="px-3 py-3 text-sm text-muted">
                Could not load sessions.
              </p>
            ) : null}
            {sessionsQuery.data?.length === 0 ? (
              <p className="px-3 py-3 text-sm text-muted">No sessions yet.</p>
            ) : null}
            {sessions.map((session: Session) => (
              <NavLink
                key={session.id}
                to={`/sessions/${session.id}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-control px-3 py-2.5 no-underline transition-colors duration-150 ${
                    isActive
                      ? "bg-panel2 text-ink"
                      : "text-muted hover:bg-panel2 hover:text-ink"
                  }`
                }
              >
                <span className="min-w-0 flex-1 truncate text-sm">{session.title}</span>
                <span className="shrink-0 text-sm tabular-nums text-muted">
                  {session.document_count}
                </span>
              </NavLink>
            ))}
          </nav>

          <div className="border-t border-line p-3">
            <ThemeToggle className="w-full justify-start" />
            <button className={`${btnGhost} w-full justify-start`} onClick={onLogout}>
              Log out
            </button>
          </div>
        </aside>
      ) : (
        <button
          type="button"
          className="fixed left-3 top-1/2 z-30 -translate-y-1/2 rounded-pill border border-line bg-bg p-2.5 text-ink shadow-[0_8px_32px_oklch(0_0_0/0.08)] transition-colors duration-150 hover:bg-panel2"
          onClick={() => setSidebarOpen(true)}
          aria-label="Show sidebar"
          title="Show sidebar"
        >
          <SidebarIcon collapsed className="h-5 w-5" />
        </button>
      )}

      <main className="relative z-10 min-w-0 flex-1 overflow-hidden">
        <Outlet />
      </main>

      <DropZone enabled={Boolean(currentSessionId)} onDrop={onDropFiles} />

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        sessions={sessions}
        onOpenSession={openSession}
        onOpenMessage={openMessage}
      />

      <Dialog
        open={manageOpen}
        onClose={closeManage}
        title="Manage sessions"
        footer={
          <>
            <button className={btnGhost} onClick={closeManage}>
              Cancel
            </button>
            <button
              className={btnDanger}
              disabled={selected.size === 0 || deleteSelected.isPending}
              onClick={() => setConfirmDelete(true)}
            >
              {deleteSelected.isPending ? (
                <>
                  <SpinnerIcon />
                  Deleting…
                </>
              ) : (
                <>Delete{selected.size > 0 ? ` (${selected.size})` : ""}</>
              )}
            </button>
          </>
        }
      >
        {sessions.length === 0 ? (
          <p className="text-sm text-muted">No sessions to manage.</p>
        ) : (
          <>
            <div className="mb-3 flex items-center justify-between">
              <button className={btnGhost} onClick={toggleAll}>
                {allSelected ? "Clear" : "Select all"}
              </button>
              <span className="text-sm tabular-nums text-muted">
                {selected.size} of {sessions.length} selected
              </span>
            </div>
            <ul className="max-h-[50vh] space-y-0.5 overflow-y-auto">
              {sessions.map((session: Session) => (
                <li key={session.id}>
                  <button
                    type="button"
                    aria-pressed={selected.has(session.id)}
                    onClick={() => toggleSelected(session.id)}
                    className={`flex w-full items-center gap-3 rounded-control px-3 py-2.5 text-left transition-colors duration-150 ${
                      selected.has(session.id) ? "bg-panel2" : "hover:bg-panel2"
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-control border transition-colors ${
                        selected.has(session.id)
                          ? "border-ink bg-ink text-onPrimary"
                          : "border-line text-transparent"
                      }`}
                    >
                      <CheckIcon />
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm">{session.title}</span>
                    <span className="shrink-0 text-sm tabular-nums text-muted">
                      {session.document_count}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
        {deleteSelected.isError ? (
          <p role="alert" className="mt-3 text-sm text-muted">
            {deleteSelected.error instanceof ApiError
              ? deleteSelected.error.message
              : "Could not delete sessions."}
          </p>
        ) : null}
      </Dialog>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete sessions?"
        danger
        pending={deleteSelected.isPending}
        pendingLabel="Deleting…"
        confirmLabel={`Delete ${selected.size}`}
        description={
          <>
            <strong className="font-medium text-ink">{selected.size}</strong>{" "}
            {selected.size === 1 ? "session" : "sessions"} and everything they own — the
            conversations, documents, and chunks — will be permanently removed.
          </>
        }
        onConfirm={() => deleteSelected.mutate(Array.from(selected))}
        onClose={() => setConfirmDelete(false)}
      />
    </div>
  );
}
