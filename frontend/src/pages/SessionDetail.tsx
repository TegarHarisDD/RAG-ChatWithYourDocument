import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type Session } from "../api";
import DocumentsPanel from "../components/DocumentsPanel";
import ChatPanel from "../components/ChatPanel";
import { ConfirmDialog, PromptDialog } from "../components/Dialog";
import { btnGhost } from "../ui";

export default function SessionDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [actionError, setActionError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);

  const sessionQuery = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => api.getSession(sessionId as string),
    enabled: Boolean(sessionId),
  });

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("cwd:last", `/sessions/${sessionId}`);
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      const last = localStorage.getItem("cwd:last");
      if (last && last !== "/sessions") {
        navigate(last, { replace: true });
      }
    }
  }, [sessionId, navigate]);

  const renameSession = useMutation<unknown, Error, string, { previous: unknown }>({
    mutationFn: (title) => api.renameSession(sessionId as string, title),
    onMutate: async (title) => {
      await queryClient.cancelQueries({ queryKey: ["session", sessionId] });
      const previous = queryClient.getQueryData(["session", sessionId]);
      queryClient.setQueryData(["session", sessionId], (old: unknown) =>
        old && typeof old === "object" ? { ...(old as object), title } : old
      );
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      return { previous };
    },
    onError: (error, _title, context) => {
      queryClient.setQueryData(["session", sessionId], context?.previous);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      setActionError(error instanceof ApiError ? error.message : "Rename failed.");
    },
    onSuccess: () => {
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  const deleteSession = useMutation<unknown, Error, void, { previous: unknown }>({
    mutationFn: () => api.deleteSession(sessionId as string),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ["sessions"] });
      const previous = queryClient.getQueryData(["sessions"]);
      queryClient.setQueryData(["sessions"], (old: unknown) =>
        Array.isArray(old)
          ? old.filter((session) => (session as Session).id !== sessionId)
          : old
      );
      return { previous };
    },
    onError: (error, _vars, context) => {
      queryClient.setQueryData(["sessions"], context?.previous);
      setActionError(error instanceof ApiError ? error.message : "Delete failed.");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      localStorage.removeItem("cwd:last");
      navigate("/sessions", { replace: true });
    },
  });

  if (!sessionId) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
        <span aria-hidden="true" className="h-3.5 w-3.5 rounded-pill bg-ink" />
        <h2 className="mt-1 text-2xl font-medium tracking-[-0.02em]">Nothing open</h2>
        <p className="max-w-xs text-sm text-muted">
          Choose a session from the sidebar, or start a new one.
        </p>
      </div>
    );
  }

  if (sessionQuery.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted">
        Opening…
      </div>
    );
  }

  if (sessionQuery.isError) {
    const notFound = sessionQuery.error instanceof ApiError && sessionQuery.error.status === 404;
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
        <h2 className="text-2xl font-medium tracking-[-0.02em]">
          {notFound ? "Session not found" : "Something went wrong"}
        </h2>
        <p className="max-w-xs text-sm text-muted">
          {notFound
            ? "This session does not exist, or it was deleted."
            : "Could not load this session."}
        </p>
      </div>
    );
  }

  const session = sessionQuery.data as Session;

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-start justify-between gap-4 px-6 py-5">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-medium tracking-[-0.02em]">{session.title}</h1>
          <p className="mt-1 text-sm text-muted">
            {session.document_count} {session.document_count === 1 ? "source" : "sources"},
            created {new Date(session.created_at).toLocaleString()}
          </p>
          {actionError ? (
            <p role="alert" className="mt-2 text-sm text-muted">
              {actionError}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <button className={btnGhost} onClick={() => setDialog("rename")}>
            Rename
          </button>
          <button className={btnGhost} onClick={() => setDialog("delete")}>
            Delete
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto p-4 lg:grid-cols-[minmax(280px,340px)_minmax(0,1fr)] lg:overflow-hidden">
        <DocumentsPanel sessionId={sessionId} />

        {session.chat_id ? (
          <ChatPanel sessionId={sessionId} chatId={session.chat_id} sessionTitle={session.title} />
        ) : (
          <section className="flex min-h-0 flex-col rounded-panel bg-panel p-5">
            <h2 className="text-base font-medium">Transcript</h2>
            <p className="mt-2 text-sm text-muted">Preparing your conversation…</p>
          </section>
        )}
      </div>

      <PromptDialog
        open={dialog === "rename"}
        title="Rename session"
        label="Session title"
        initialValue={session.title}
        onConfirm={(title) => {
          renameSession.mutate(title);
          setDialog(null);
        }}
        onClose={() => setDialog(null)}
      />

      <ConfirmDialog
        open={dialog === "delete"}
        title="Delete session?"
        danger
        description={
          <>
            <strong className="font-medium text-ink">{session.title}</strong> and everything it
            owns — the conversation, documents, and chunks — will be permanently removed.
          </>
        }
        onConfirm={() => {
          deleteSession.mutate();
          setDialog(null);
        }}
        onClose={() => setDialog(null)}
      />
    </div>
  );
}
