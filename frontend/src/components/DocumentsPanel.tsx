import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError, type Document } from "../api";
import { ConfirmDialog, PromptDialog } from "./Dialog";
import { SpinnerIcon } from "./icons";
import { btnGhost, btnSecondary } from "../ui";

function statusLabel(document: Document): string {
  if (document.status === "ready") {
    return `${document.chunk_count} ${document.chunk_count === 1 ? "chunk" : "chunks"}`;
  }
  return document.status;
}

function statusClass(status: Document["status"]): string {
  switch (status) {
    case "ready":
      return "text-ink";
    case "failed":
      return "text-ink font-medium";
    default:
      return "text-muted";
  }
}

export default function DocumentsPanel({ sessionId }: { sessionId: string }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [uploadLabel, setUploadLabel] = useState<string | null>(null);
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
    mutationFn: (files: File[]) => {
      setUploadPercent(0);
      setUploadLabel(files.length === 1 ? files[0].name : `${files.length} files`);
      return api.uploadDocuments(sessionId, files, setUploadPercent);
    },
    onMutate: () => setUploadError(null),
    onSuccess: (created: Document[]) => {
      if (inputRef.current) inputRef.current.value = "";
      queryClient.setQueryData(["documents", sessionId], (old: unknown) => {
        const existing = Array.isArray(old) ? (old as Document[]) : [];
        const ids = new Set(created.map((doc) => doc.id));
        return [...existing.filter((doc) => !ids.has(doc.id)), ...created];
      });
      invalidate();
    },
    onSettled: () => {
      setUploadLabel(null);
      setUploadPercent(0);
    },
    onError: (error) => {
      setUploadError(error instanceof ApiError ? error.message : "Upload failed.");
    },
  });

  // Files dropped anywhere on the window are routed here by the global DropZone.
  useEffect(() => {
    function onDroppedFiles(event: Event) {
      const files = (event as CustomEvent<File[]>).detail;
      if (files && files.length > 0 && !upload.isPending) upload.mutate(files);
    }
    window.addEventListener("cwd:drop-files", onDroppedFiles);
    return () => window.removeEventListener("cwd:drop-files", onDroppedFiles);
  }, [upload]);

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
    <section className="flex min-h-0 flex-col rounded-panel bg-panel lg:overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-5 py-4">
        <h2 className="text-base font-medium">
          Corpus
          {documents.length ? (
            <span className="ml-2 text-sm tabular-nums text-muted">{documents.length}</span>
          ) : null}
        </h2>
        <button
          className={btnSecondary}
          onClick={() => inputRef.current?.click()}
          disabled={upload.isPending}
        >
          {upload.isPending ? (
            <>
              <SpinnerIcon />
              Adding…
            </>
          ) : (
            "Add files"
          )}
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
        <div role="status" aria-live="polite" className="px-5 pb-3">
          <div className="flex items-center gap-2 text-sm text-muted">
            <SpinnerIcon className="h-3.5 w-3.5 shrink-0 text-ink" />
            <span className="min-w-0 flex-1 truncate">Uploading {uploadLabel}…</span>
            <span className="shrink-0 tabular-nums">{uploadPercent}%</span>
          </div>
          <div className="mt-2 h-1 w-full overflow-hidden rounded-pill bg-panel2">
            <div
              role="progressbar"
              aria-label="Upload progress"
              aria-valuenow={uploadPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-full rounded-pill bg-ink transition-[width] duration-200 ease-out"
              style={{ width: `${uploadPercent}%` }}
            />
          </div>
        </div>
      ) : null}
      {uploadError ? (
        <p role="alert" className="px-5 pb-3 text-sm text-muted">
          {uploadError}
        </p>
      ) : null}
      {actionError ? (
        <p role="alert" className="px-5 pb-3 text-sm text-muted">
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
          <p role="alert" className="py-3 text-sm text-muted">
            Could not load documents.
          </p>
        ) : null}
        {!documentsQuery.isLoading && documents.length === 0 ? (
          <div className="my-3 rounded-panel border border-dashed border-line px-4 py-10 text-center">
            <p className="text-sm text-muted">The corpus is empty.</p>
            <p className="mt-2 text-[13px] text-muted">
              Drop files anywhere, or use Add files.
            </p>
          </div>
        ) : null}

        <ul>
          {documents.map((document) => (
            <li key={document.id} className="border-b border-line py-3 last:border-b-0">
              <div className="flex items-center justify-between gap-3">
                <span className="min-w-0 flex-1 truncate text-sm">{document.filename}</span>
                <span
                  className={`inline-flex shrink-0 items-center rounded-pill px-2.5 py-1 text-[13px] ${statusClass(
                    document.status
                  )}`}
                >
                  {statusLabel(document)}
                </span>
              </div>
              {document.status === "failed" && document.error ? (
                <p className="mt-1.5 text-sm text-muted">{document.error}</p>
              ) : null}
              <div className="mt-2 flex gap-1">
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
                <button className={btnGhost} onClick={() => onDelete(document)}>
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
