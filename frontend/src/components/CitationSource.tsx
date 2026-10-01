import { useQuery } from "@tanstack/react-query";
import { api, ApiError, type Citation } from "../api";
import { formatLocator } from "../locator";
import { btnGhost } from "../ui";

export default function CitationSource({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  const chunkQuery = useQuery({
    queryKey: ["chunk", citation.chunk_id],
    queryFn: () => api.getChunk(citation.chunk_id),
  });

  const locator = formatLocator(citation.locator);

  return (
    <section
      aria-label="Source passage"
      className="mt-3 rounded-panel bg-bg px-4 py-3"
    >
      <div className="flex items-baseline gap-3">
        <span className="shrink-0 text-sm text-muted">[{citation.index}]</span>
        <strong className="min-w-0 flex-1 truncate text-sm font-medium">
          {citation.filename}
        </strong>
        {locator ? <span className="shrink-0 text-sm text-muted">{locator}</span> : null}
        <button
          className={`${btnGhost} shrink-0`}
          onClick={onClose}
          aria-label="Close source passage"
        >
          Close
        </button>
      </div>

      {chunkQuery.isLoading ? (
        <p role="status" className="mt-3 text-sm text-muted">
          Retrieving passage…
        </p>
      ) : null}
      {chunkQuery.isError ? (
        <p role="alert" className="mt-3 text-sm text-muted">
          {chunkQuery.error instanceof ApiError && chunkQuery.error.status === 404
            ? "This source passage is no longer available."
            : "Could not load the source passage."}
        </p>
      ) : null}
      {chunkQuery.data ? (
        <blockquote className="mt-3 border-l border-line pl-4 text-[0.95rem] leading-relaxed text-muted">
          {chunkQuery.data.text}
        </blockquote>
      ) : null}
    </section>
  );
}
