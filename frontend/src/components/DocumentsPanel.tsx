import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type Document } from "../api";
import { ConfirmDialog, PromptDialog } from "./Dialog";
import { btnGhost } from "../ui";

function statusLabel(document: Document): string {
  if (document.status === "ready") {
    return `${document.chunk_count} ${document.chunk_count === 1 ? "chunk" : "chunks"}`;
  }
  return document.status;
}

function statusClass(status: Document["status"]): string {
  switch (status) {
    case "ready":
      return "border-success/40 text-success";
    case "failed":
      return "border-danger/40 text-danger";
    default:
      return "border-warning/40 text-warning";
  }
}

export default function DocumentsPanel({ sessionId }: { sessionId: string }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<
    { type: "rename" | "delete"; document: Document } | null
  >(null);

  const documentsQuery = useQuery({
    queryKey: ["documents", sessionId],
    queryFn: () => api.listDocuments(sessionId),
    refetchInterval: (query) => {
      const data = query.state.data as Document[] | undefined;
      const active = data?.some((d) => d.status === "pending" || d.status === "processing");
      return active ? 1500 : false;
    },
  });

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["documents", sessionId] });
    queryClient.invalidateQueries({ queryKey: ["sessions"] });
  }

  const upload = useMutation({
    mutationFn: (files: File[]) => api.uploadDocuments(sessionId, files),
    onMutate: () => setUploadError(null),
    onSuccess: () => {
      if (inputRef.current) inputRef.current.value = "";
      invalidate();
    },
    onError: (error) => {
      setUploadError(error instanceof ApiError ? error.message : "Upload failed.");
    },
  });

  const renameDocument = useMutation<
    unknown,
    Error,
    { id: string; filename: string },
    { previous: unknown }
  >({
    mutationFn: ({ id, filename }) => api.renameDocument(id, filename),
    onMutate: async ({ id, filename }) => {
      await queryClient.cancelQueries({ queryKey: ["documents", sessionId] });
      const previous = queryClient.getQueryData(["documents", sessionId]);
      queryClient.setQueryData(["documents", sessionId], (old: unknown) =>
        Array.isArray(old)
          ? old.map((doc) =>
              (doc as Document).id === id ? { ...(doc as Document), filename } : doc
            )
          : old
      );
      return { previous };
    },
    onError: (error, _vars, context) => {
      queryClient.setQueryData(["documents", sessionId], context?.previous);
      setActionError(error instanceof ApiError ? error.message : "Rename failed.");
    },
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
  });

  const deleteDocument = useMutation<unknown, Error, string, { previous: unknown }>({
    mutationFn: (id) => api.deleteDocument(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["documents", sessionId] });
      const previous = queryClient.getQueryData(["documents", sessionId]);
      queryClient.setQueryData(["documents", sessionId], (old: unknown) =>
        Array.isArray(old) ? old.filter((doc) => (doc as Document).id !== id) : old
      );
      return { previous };
    },
    onError: (error, _id, context) => {
      queryClient.setQueryData(["documents", sessionId], context?.previous);
      setActionError(error instanceof ApiError ? error.message : "Delete failed.");
    },
    onSuccess: () => {
      setActionError(null);
      invalidate();
    },
  });

  const reprocessDocument = useMutation({
    mutationFn: (id: string) => api.reprocessDocument(id),
    onSuccess: invalidate,
    onError: (error) =>
      setActionError(error instanceof ApiError ? error.message : "Could not re-process."),
  });

  function onFilesChosen(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (files.length > 0) {
      upload.mutate(files);
    }
  }

  function onRename(document: Document) {
    setDialog({ type: "rename", document });
  }

  function onDelete(document: Document) {
    setDialog({ type: "delete", document });
  }

  const documents = documentsQuery.data ?? [];

  return (
    <section className="flex min-h-0 flex-col border border-line bg-panel lg:overflow-hidden">
      <div className="flex items-baseline justify-between gap-2 border-b border-line px-5 py-3">
        <h2 className="font-display text-base">
          Corpus
          {documents.length ? (
            <span className="ml-2 font-mono text-[11px] tabular-nums text-faint">
              {documents.length}
            </span>
          ) : null}
        </h2>
        <button className={btnGhost} onClick={() => inputRef.current?.click()}>
          + Add
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.md,.markdown,.json,.pdf,.docx,text/plain,text/markdown,application/json,application/pdf"
          onChange={onFilesChosen}
          hidden
        />
      </div>

      {upload.isPending ? (
        <p role="status" className="border-b border-line px-5 py-2 font-mono text-[11px] text-faint">
          uploading…
        </p>
      ) : null}
      {uploadError ? (
        <p
          role="alert"
          className="border-b border-line bg-danger/5 px-5 py-2 font-reading text-xs text-danger"
        >
          {uploadError}
        </p>
      ) : null}
      {actionError ? (
        <p
          role="alert"
          className="border-b border-line bg-danger/5 px-5 py-2 font-reading text-xs text-danger"
        >
          {actionError}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-5">
        {documentsQuery.isLoading ? (
          <div aria-busy="true" className="space-y-3 py-3">
            <div className="skeleton h-14 w-full" />
            <div className="skeleton h-14 w-full" />
          </div>
        ) : null}
        {documentsQuery.isError ? (
          <p role="alert" className="py-3 font-reading text-xs text-danger">
            Could not load documents.
          </p>
        ) : null}
        {!documentsQuery.isLoading && documents.length === 0 ? (
          <div className="my-4 border border-dashed border-line px-4 py-8 text-center">
            <p className="font-reading text-sm italic text-muted">The corpus is empty.</p>
            <p className="mt-2 font-mono text-[10px] tracking-wide text-faint">
              PDF · DOCX · TXT · Markdown · JSON
            </p>
          </div>
        ) : null}

        <ul>
          {documents.map((document) => (
            <li key={document.id} className="border-b border-line/60 py-3 last:border-b-0">
              <div className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 flex-1 truncate font-reading text-sm">
                  {document.filename}
                </span>
                <span
                  className={`inline-flex shrink-0 items-center gap-1.5 border px-2 py-0.5 font-mono text-[10px] tracking-wide ${statusClass(
                    document.status
                  )}`}
                >
                  <span aria-hidden="true" className="h-1.5 w-1.5 bg-current" />
                  {statusLabel(document)}
                </span>
              </div>
              {document.status === "failed" && document.error ? (
                <p className="mt-1.5 font-reading text-xs text-danger">{document.error}</p>
              ) : null}
              <div className="mt-2 flex gap-3">
                <button className={btnGhost} onClick={() => onRename(document)}>
                  Rename
                </button>
                <button
                  className={btnGhost}
                  onClick={() => reprocessDocument.mutate(document.id)}
                  disabled={reprocessDocument.isPending}
                >
                  Reprocess
                </button>
                <button
                  className={`${btnGhost} hover:text-danger`}
                  onClick={() => onDelete(document)}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <PromptDialog
        open={dialog?.type === "rename"}
        title="Rename document"
        label="File name"
        initialValue={dialog?.document.filename ?? ""}
        onConfirm={(filename) => {
          if (dialog) renameDocument.mutate({ id: dialog.document.id, filename });
          setDialog(null);
        }}
        onClose={() => setDialog(null)}
      />

      <ConfirmDialog
        open={dialog?.type === "delete"}
        title="Delete document?"
        danger
        description={
          <>
            <strong className="font-medium text-ink">{dialog?.document.filename}</strong> and its
            chunks will be permanently removed from this session.
          </>
        }
        onConfirm={() => {
          if (dialog) deleteDocument.mutate(dialog.document.id);
          setDialog(null);
        }}
        onClose={() => setDialog(null)}
      />
    </section>
  );
}
