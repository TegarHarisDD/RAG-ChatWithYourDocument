import { useEffect, useMemo, useRef, useState } from "react";
import { api, type MessageSearchResult, type Session } from "../api";

interface PaletteItem {
  key: string;
  label: string;
  hint: string;
  run: () => void;
}

export default function CommandPalette({
  open,
  onClose,
  sessions,
  onOpenSession,
  onOpenMessage,
}: {
  open: boolean;
  onClose: () => void;
  sessions: Session[];
  onOpenSession: (session: Session) => void;
  onOpenMessage: (result: MessageSearchResult) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [results, setResults] = useState<MessageSearchResult[]>([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    if (open && !element.open) {
      element.showModal();
      setQuery("");
      setResults([]);
      setActive(0);
    } else if (!open && element.open) {
      element.close();
    }
  }, [open]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(query.trim()), 180);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    if (!debounced) {
      setResults([]);
      return;
    }
    let cancelled = false;
    api
      .searchMessages(debounced, 8)
      .then((hits) => {
        if (!cancelled) setResults(hits);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      });
    return () => {
      cancelled = true;
    };
  }, [debounced]);

  const items = useMemo<PaletteItem[]>(() => {
    const q = query.trim().toLowerCase();
    const matches = (text: string) => !q || text.toLowerCase().includes(q);
    const list: PaletteItem[] = [];
    for (const session of sessions) {
      if (matches(session.title)) {
        list.push({
          key: `s-${session.id}`,
          label: session.title || "Untitled session",
          hint: "session",
          run: () => onOpenSession(session),
        });
      }
    }
    for (const hit of results) {
      list.push({
        key: `m-${hit.message_id}`,
        label: hit.snippet || hit.session_title,
        hint: hit.session_title || "message",
        run: () => onOpenMessage(hit),
      });
    }
    return list;
  }, [query, results, sessions, onOpenSession, onOpenMessage]);

  useEffect(() => {
    setActive(0);
  }, [query, results.length]);

  function run(item: PaletteItem) {
    onClose();
    item.run();
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, items.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const item = items[active];
      if (item) run(item);
    }
  }

  return (
    <dialog
      ref={ref}
      aria-label="Command palette"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className="m-auto w-[min(92vw,34rem)] overflow-hidden border border-line bg-raised p-0 text-ink shadow-[0_24px_60px_-20px_rgba(12,18,28,0.55)] ring-1 ring-black/5 dark:ring-white/10"
    >
      <div className="border-b border-line px-4 py-3">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Search sessions and messages…"
          aria-label="Search sessions and messages"
          className="w-full bg-transparent font-reading text-base text-ink outline-none placeholder:text-faint"
        />
      </div>
      <ul className="max-h-[60vh] overflow-y-auto py-1">
        {items.length === 0 ? (
          <li className="px-4 py-3 font-reading text-sm italic text-muted">
            {query.trim() ? "No matches." : "Type to search sessions and messages."}
          </li>
        ) : (
          items.map((item, index) => (
            <li key={item.key}>
              <button
                type="button"
                onMouseEnter={() => setActive(index)}
                onClick={() => run(item)}
                className={`flex w-full items-baseline gap-3 px-4 py-2 text-left transition-colors ${
                  index === active ? "bg-panel2" : "hover:bg-panel2/60"
                }`}
              >
                <span className="min-w-0 flex-1 truncate font-reading text-sm">{item.label}</span>
                <span className="shrink-0 font-mono text-[10px] tracking-wide text-faint">
                  {item.hint}
                </span>
              </button>
            </li>
          ))
        )}
      </ul>
    </dialog>
  );
}
