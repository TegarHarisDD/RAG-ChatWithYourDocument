import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  ApiError,
  streamMessage,
  type Citation,
  type Document,
  type Message,
  type Source,
} from "../api";
import { conversationToMarkdown, downloadTextFile, slugify } from "../export";
import { formatLocator } from "../locator";
import CitationSource from "./CitationSource";
import MessageContent from "./MessageContent";
import { ConfirmDialog } from "./Dialog";
import { CopyIcon, CopySourcesIcon, EditIcon, RegenerateIcon, TrashIcon } from "./icons";
import { btnDanger, btnGhost, btnPrimary } from "../ui";

function ActionButton({
  label,
  onClick,
  disabled = false,
  danger = false,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  children: React.ReactNode;
}) {
  const tone = danger
    ? "border-line text-muted hover:border-danger hover:text-danger"
    : "border-line text-muted hover:border-accent hover:text-accent";
  return (
    <button
      type="button"
      className={`flex h-7 w-7 items-center justify-center border transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-40 ${tone}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}

function finishNote(reason: string | null): string | null {
  switch (reason) {
    case "stopped":
      return "stopped mid-answer";
    case "no_documents":
      return "no sources yet";
    case "nothing_relevant":
      return "nothing relevant found";
    default:
      return null;
  }
}

function withSources(message: Message): string {
  if (!message.citations.length) return message.content;
  const sources = message.citations
    .map((citation) => {
      const locator = formatLocator(citation.locator);
      return `[${citation.index}] ${citation.filename}${locator ? ` (${locator})` : ""}`;
    })
    .join("\n");
  return `${message.content}\n\nSources:\n${sources}`;
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    /* Clipboard can be unavailable (insecure context); ignore. */
  }
}

export default function ChatPanel({
  sessionId,
  chatId,
  sessionTitle,
}: {
  sessionId: string;
  chatId: string;
  sessionTitle: string;
}) {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [liveCitations, setLiveCitations] = useState<Citation[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [guardrail, setGuardrail] = useState<{ reason: string; message: string } | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState<Citation | null>(null);
  const [clearOpen, setClearOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Message | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLLIElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  const chatQuery = useQuery({
    queryKey: ["chat", chatId],
    queryFn: () => api.getChat(chatId),
  });

  const messagesQuery = useQuery({
    queryKey: ["messages", chatId],
    queryFn: () => api.listMessages(chatId),
  });

  // Shared with the document panel: chat is only available once at least one
  // document has finished processing.
  const documentsQuery = useQuery({
    queryKey: ["documents", sessionId],
    queryFn: () => api.listDocuments(sessionId),
    refetchInterval: (query) => {
      const data = query.state.data as Document[] | undefined;
      const active = data?.some((d) => d.status === "pending" || d.status === "processing");
      return active ? 1500 : false;
    },
  });
  const hasReadyDocument = (documentsQuery.data ?? []).some((d) => d.status === "ready");

  useEffect(() => {
    setInput("");
    setStreaming(false);
    setStreamText("");
    setLiveCitations([]);
    setSources([]);
    setGuardrail(null);
    setStreamError(null);
    setActionError(null);
    setRevealed(null);
    setEditingId(null);
    setPendingDelete(null);
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messagesQuery.data, streamText, guardrail, streamError]);

  // Jump to a message referenced by ?m=<id> (from command-palette search).
  const targetMessageId = searchParams.get("m");
  useEffect(() => {
    if (!targetMessageId || !messagesQuery.data) return;
    const element = document.getElementById(`m-${targetMessageId}`);
    if (!element) return;
    element.scrollIntoView({ block: "center" });
    element.classList.add("flash");
    const timer = window.setTimeout(() => element.classList.remove("flash"), 1700);
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        next.delete("m");
        return next;
      },
      { replace: true }
    );
    return () => window.clearTimeout(timer);
  }, [targetMessageId, messagesQuery.data, setSearchParams]);

  // Global "/" shortcut asks us to focus the composer.
  useEffect(() => {
    function focusComposer() {
      composerRef.current?.focus();
    }
    window.addEventListener("cwd:focus-composer", focusComposer);
    return () => window.removeEventListener("cwd:focus-composer", focusComposer);
  }, []);

  const clearMessages = useMutation({
    mutationFn: () => api.clearMessages(chatId),
    onSuccess: () => {
      setRevealed(null);
      setStreamError(null);
      queryClient.invalidateQueries({ queryKey: ["messages", chatId] });
    },
    onError: (error) =>
      setActionError(
        error instanceof ApiError ? error.message : "Could not clear the conversation."
      ),
  });

  function handleEvent(event: string, data: Record<string, unknown>) {
    switch (event) {
      case "user": {
        const messageId = typeof data.message_id === "string" ? data.message_id : null;
        if (messageId) {
          queryClient.setQueryData(["messages", chatId], (old: Message[] | undefined) =>
            (old ?? []).map((message) =>
              message.id.startsWith("temp-") && message.role === "user"
                ? { ...message, id: messageId }
                : message
            )
          );
        }
        break;
      }
      case "sources":
        setSources((data.sources as Source[]) ?? []);
        break;
      case "token":
        setStreamText((text) => text + (typeof data.text === "string" ? data.text : ""));
        break;
      case "citations":
        setLiveCitations((data.citations as Citation[]) ?? []);
        break;
      case "guardrail":
        setGuardrail({ reason: String(data.reason), message: String(data.message) });
        break;
      case "error":
        setStreamError(
          typeof data.message === "string" ? data.message : "The model is unavailable."
        );
        break;
      default:
        break;
    }
  }

  async function sendQuestion(raw: string) {
    const content = raw.trim();
    if (!content || streaming || !hasReadyDocument) return;

    setGuardrail(null);
    setStreamError(null);
    setSources([]);
    setStreamText("");
    setLiveCitations([]);
    setRevealed(null);

    const tempId = `temp-${Date.now()}`;
    queryClient.setQueryData(["messages", chatId], (old: Message[] | undefined) => [
      ...(old ?? []),
      {
        id: tempId,
        chat_id: chatId,
        session_id: sessionId,
        role: "user" as const,
        content,
        citations: [],
        created_at: new Date().toISOString(),
        model: null,
        finish_reason: null,
      },
    ]);

    setStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;
    let aborted = false;

    try {
      await streamMessage(chatId, content, handleEvent, controller.signal);
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        aborted = true;
      } else if (error instanceof ApiError && error.status === 401) {
        window.location.assign("/login");
      } else {
        setStreamError(error instanceof ApiError ? error.message : "Something went wrong.");
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      if (aborted) {
        // Give the server a moment to persist the partial before re-reading.
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      setStreamText("");
      setLiveCitations([]);
      queryClient.invalidateQueries({ queryKey: ["messages", chatId] });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    }
  }

  function onSend() {
    const content = input.trim();
    if (!content) return;
    setInput("");
    void sendQuestion(content);
  }

  function onStop() {
    abortRef.current?.abort();
  }

  function onClear() {
    setClearOpen(true);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void onSend();
    }
  }

  function truncateCacheTo(index: number) {
    queryClient.setQueryData(["messages", chatId], (old: Message[] | undefined) =>
      (old ?? []).slice(0, index)
    );
  }

  async function onRegenerate(message: Message) {
    if (streaming) return;
    const index = messages.findIndex((item) => item.id === message.id);
    if (index < 0) return;
    let userIndex = index;
    while (userIndex >= 0 && messages[userIndex].role !== "user") userIndex--;
    if (userIndex < 0) return;

    const question = messages[userIndex].content;
    await api.truncateMessages(chatId, messages[userIndex].id);
    truncateCacheTo(userIndex);
    await sendQuestion(question);
  }

  async function onSubmitEdit(message: Message) {
    const value = editValue.trim();
    if (!value || streaming) return;
    const index = messages.findIndex((item) => item.id === message.id);
    if (index < 0) return;

    setEditingId(null);
    await api.truncateMessages(chatId, message.id);
    truncateCacheTo(index);
    await sendQuestion(value);
  }

  function onConfirmDelete() {
    if (!pendingDelete) return;
    const id = pendingDelete.id;
    setPendingDelete(null);
    api
      .deleteMessage(chatId, id)
      .then(() => queryClient.invalidateQueries({ queryKey: ["messages", chatId] }))
      .catch((error) =>
        setActionError(error instanceof ApiError ? error.message : "Could not delete message.")
      );
  }

  function onExport() {
    const markdown = conversationToMarkdown(sessionTitle, messages);
    downloadTextFile(`${slugify(sessionTitle)}.md`, markdown);
  }

  if (chatQuery.isError) {
    const notFound = chatQuery.error instanceof ApiError && chatQuery.error.status === 404;
    return (
      <div className="flex min-h-0 flex-col items-center justify-center gap-2 border border-line bg-panel p-8 text-center">
        <h2 className="font-display text-xl font-medium">
          {notFound ? "Conversation not found" : "Something went wrong"}
        </h2>
        <p className="font-reading text-sm italic text-muted">
          {notFound ? "This conversation was deleted." : "Could not load this conversation."}
        </p>
      </div>
    );
  }

  const messages = messagesQuery.data ?? [];
  const composerDisabled = streaming || !hasReadyDocument;

  return (
    <section
      id="transcript"
      className="flex min-h-0 flex-col border border-line bg-panel lg:overflow-hidden"
    >
      <div className="flex items-baseline justify-between gap-2 border-b border-line px-5 py-3">
        <h2 className="font-display text-base">Transcript</h2>
        <div className="flex items-center gap-1 print:hidden">
          <button
            className={btnGhost}
            onClick={onExport}
            disabled={messages.length === 0}
            title="Download as Markdown"
          >
            Export
          </button>
          <button
            className={btnGhost}
            onClick={() => window.print()}
            disabled={messages.length === 0}
            title="Print or save as PDF"
          >
            Print
          </button>
          <button className={btnGhost} onClick={onClear} disabled={messages.length === 0}>
            Clear
          </button>
        </div>
      </div>

      {actionError ? (
        <p
          role="alert"
          className="border-b border-line bg-danger/5 px-5 py-2 font-reading text-xs text-danger"
        >
          {actionError}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        <h2 className="mb-4 hidden font-display text-xl font-medium print:block">
          {sessionTitle}
        </h2>

        {messagesQuery.isLoading ? (
          <div aria-busy="true" className="space-y-4">
            <div className="skeleton h-10 w-2/3" />
            <div className="skeleton h-20 w-full" />
          </div>
        ) : null}
        {messagesQuery.isError ? (
          <p role="alert" className="font-reading text-xs text-danger">
            Could not load messages.
          </p>
        ) : null}
        {!messagesQuery.isLoading && messages.length === 0 && !streaming ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <span aria-hidden="true" className="font-mono text-xl text-accent">
              ¶
            </span>
            <p className="max-w-xs font-reading text-sm italic text-muted">
              {hasReadyDocument
                ? "Ask a question about this session's documents below."
                : "Add a document to the corpus to begin."}
            </p>
          </div>
        ) : null}

        <ul className="space-y-6">
          {messages.map((message) => {
            const isUser = message.role === "user";
            const note = isUser ? null : finishNote(message.finish_reason);
            const isEditing = editingId === message.id;
            return (
              <li
                key={message.id}
                id={`m-${message.id}`}
                className="group grid scroll-mt-6 grid-cols-[1.5rem_minmax(0,1fr)] gap-x-3"
              >
                <span
                  aria-hidden="true"
                  className={`select-none pt-0.5 font-mono text-sm ${
                    isUser ? "text-accent" : "text-faint"
                  }`}
                >
                  {isUser ? "?" : "¶"}
                </span>
                <div
                  className={
                    isUser
                      ? "border-l border-accent/40 pl-4"
                      : "border-t border-line pt-4"
                  }
                >
                  {note ? (
                    <p className="mb-2 font-mono text-[10px] tracking-wide text-faint">{note}</p>
                  ) : null}

                  {isEditing ? (
                    <div className="flex flex-col gap-2">
                      <textarea
                        aria-label="Edit question"
                        autoFocus
                        rows={2}
                        className="w-full resize-none border border-line bg-bg px-3 py-2 font-reading text-base leading-relaxed text-ink outline-none focus:border-accent"
                        value={editValue}
                        onChange={(event) => setEditValue(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            void onSubmitEdit(message);
                          } else if (event.key === "Escape") {
                            setEditingId(null);
                          }
                        }}
                      />
                      <div className="flex gap-3">
                        <button className={btnPrimary} onClick={() => void onSubmitEdit(message)}>
                          Send again
                        </button>
                        <button className={btnGhost} onClick={() => setEditingId(null)}>
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : isUser ? (
                    <p className="whitespace-pre-wrap break-words font-reading text-lg leading-snug text-ink">
                      {message.content}
                    </p>
                  ) : (
                    <MessageContent
                      content={message.content}
                      citations={message.citations}
                      onCitation={setRevealed}
                    />
                  )}

                  {!isEditing ? (
                    <div className="mt-2 flex flex-wrap items-center gap-1.5 print:hidden">
                      <ActionButton label="Copy" onClick={() => void copyText(message.content)}>
                        <CopyIcon />
                      </ActionButton>
                      {isUser ? (
                        <>
                          <ActionButton
                            label="Edit and resend"
                            onClick={() => {
                              setEditingId(message.id);
                              setEditValue(message.content);
                            }}
                            disabled={streaming}
                          >
                            <EditIcon />
                          </ActionButton>
                          <ActionButton
                            label="Delete"
                            onClick={() => setPendingDelete(message)}
                            danger
                          >
                            <TrashIcon />
                          </ActionButton>
                        </>
                      ) : (
                        <>
                          <ActionButton
                            label="Copy with sources"
                            onClick={() => void copyText(withSources(message))}
                          >
                            <CopySourcesIcon />
                          </ActionButton>
                          <ActionButton
                            label="Regenerate"
                            onClick={() => void onRegenerate(message)}
                            disabled={streaming || !hasReadyDocument}
                          >
                            <RegenerateIcon />
                          </ActionButton>
                          <ActionButton
                            label="Delete"
                            onClick={() => setPendingDelete(message)}
                            danger
                          >
                            <TrashIcon />
                          </ActionButton>
                        </>
                      )}
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}

          {streaming ? (
            <li className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-3">
              <span
                aria-hidden="true"
                className="select-none pt-0.5 font-mono text-sm text-faint"
              >
                ¶
              </span>
              <div className="border-t border-line pt-4">
                {guardrail ? null : streamText ? (
                  <MessageContent
                    content={streamText}
                    citations={liveCitations}
                    onCitation={setRevealed}
                    trailing={<span className="caret" aria-hidden="true" />}
                  />
                ) : (
                  <p
                    role="status"
                    aria-live="polite"
                    className="font-mono text-[11px] text-faint"
                  >
                    retrieving sources…
                  </p>
                )}
              </div>
            </li>
          ) : null}
          <li ref={bottomRef} />
        </ul>
      </div>

      {guardrail ? (
        <div
          role="status"
          className="mx-5 mt-3 border-l-2 border-accent bg-panel2/60 px-4 py-3"
        >
          <p className="font-mono text-[10px] tracking-wide text-accent">
            {guardrail.reason === "no_documents" ? "no sources yet" : "nothing relevant"}
          </p>
          <p className="mt-1 font-reading text-sm text-ink/90">{guardrail.message}</p>
        </div>
      ) : null}

      {streamError ? (
        <div role="alert" className="mx-5 mt-3 border-l-2 border-danger bg-danger/5 px-4 py-3">
          <p className="font-mono text-[10px] tracking-wide text-danger">model unavailable</p>
          <p className="mt-1 font-reading text-sm text-ink/90">{streamError}</p>
        </div>
      ) : null}

      {sources.length ? (
        <p className="mx-5 mt-3 font-mono text-[10px] tracking-wide text-faint">
          grounded in {sources.length} {sources.length === 1 ? "source" : "sources"}:{" "}
          {sources.map((source) => source.filename).join(", ")}
        </p>
      ) : null}

      {revealed ? (
        <div className="mx-5">
          <CitationSource citation={revealed} onClose={() => setRevealed(null)} />
        </div>
      ) : null}

      <div className="mt-4 border-t border-line px-5 pt-4 print:hidden">
        <div className="flex items-end gap-3">
          <textarea
            ref={composerRef}
            aria-label="Ask a question about this session's documents"
            className="min-h-[3rem] flex-1 resize-none border border-line bg-bg px-3 py-2 font-reading text-base leading-relaxed text-ink outline-none transition-colors duration-200 placeholder:text-faint focus:border-accent disabled:opacity-50"
            value={input}
            rows={2}
            placeholder={
              hasReadyDocument
                ? "Ask a question about these documents…"
                : "Add a document to the corpus to begin"
            }
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onKeyDown}
            disabled={composerDisabled}
          />
          {streaming ? (
            <button className={btnDanger} onClick={onStop} aria-label="Stop generating">
              Stop
            </button>
          ) : (
            <button
              className={btnPrimary}
              onClick={() => void onSend()}
              disabled={!input.trim() || !hasReadyDocument}
            >
              Send
            </button>
          )}
        </div>
        <p className="mt-2 font-mono text-[10px] tracking-wide text-faint">
          Enter to send · Shift + Enter for a new line · Ctrl/⌘K to search
        </p>
      </div>

      <ConfirmDialog
        open={clearOpen}
        title="Clear conversation?"
        confirmLabel="Clear"
        danger
        description="The messages are removed. The session and its documents stay."
        onConfirm={() => {
          clearMessages.mutate();
          setClearOpen(false);
        }}
        onClose={() => setClearOpen(false)}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete message?"
        danger
        description={
          <>
            This message and its{" "}
            {pendingDelete?.role === "user" ? "answer" : "question"} will be removed from the
            transcript.
          </>
        }
        onConfirm={onConfirmDelete}
        onClose={() => setPendingDelete(null)}
      />
    </section>
  );
}
