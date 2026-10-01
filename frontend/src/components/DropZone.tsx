import { useEffect, useRef, useState } from "react";

function carriesFiles(event: DragEvent): boolean {
  const types = event.dataTransfer?.types;
  if (!types) return false;
  return Array.from(types).includes("Files");
}

// A window-wide drop target. While files are dragged anywhere over the app it
// raises a full-screen cue; releasing them hands the files to `onDrop`. Drop
// events are always swallowed so the browser never navigates to a loose file,
// even when dropping is unavailable.
export default function DropZone({
  onDrop,
  enabled,
}: {
  onDrop: (files: File[]) => void;
  enabled: boolean;
}) {
  const [active, setActive] = useState(false);
  const depth = useRef(0);
  const onDropRef = useRef(onDrop);
  const enabledRef = useRef(enabled);

  useEffect(() => {
    onDropRef.current = onDrop;
    enabledRef.current = enabled;
  });

  useEffect(() => {
    function reset() {
      depth.current = 0;
      setActive(false);
    }

    function enter(event: DragEvent) {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      depth.current += 1;
      setActive(true);
    }

    function over(event: DragEvent) {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = enabledRef.current ? "copy" : "none";
      }
    }

    function leave(event: DragEvent) {
      if (!carriesFiles(event)) return;
      depth.current = Math.max(0, depth.current - 1);
      if (depth.current === 0) setActive(false);
    }

    function drop(event: DragEvent) {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      const files = Array.from(event.dataTransfer?.files ?? []);
      reset();
      if (enabledRef.current && files.length > 0) onDropRef.current(files);
    }

    window.addEventListener("dragenter", enter);
    window.addEventListener("dragover", over);
    window.addEventListener("dragleave", leave);
    window.addEventListener("drop", drop);
    window.addEventListener("dragend", reset);
    window.addEventListener("blur", reset);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragover", over);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("drop", drop);
      window.removeEventListener("dragend", reset);
      window.removeEventListener("blur", reset);
    };
  }, []);

  if (!active) return null;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-40 flex items-center justify-center bg-bg/75 p-6 backdrop-blur-sm"
    >
      <div
        className={`flex w-full max-w-md flex-col items-center gap-3 rounded-panel border-2 border-dashed px-10 py-10 text-center shadow-[0_8px_32px_oklch(0_0_0/0.08)] ${
          enabled ? "border-ink bg-raised" : "border-line bg-panel"
        }`}
      >
        <span
          aria-hidden="true"
          className={`flex h-12 w-12 items-center justify-center rounded-pill ${
            enabled ? "bg-panel2 text-ink" : "bg-panel2 text-muted"
          }`}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-6 w-6"
          >
            <path d="M12 16V4" />
            <path d="M7 9l5-5 5 5" />
            <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
          </svg>
        </span>
        <p className="text-lg font-medium tracking-[-0.015em]">
          {enabled ? "Drop to add to this session" : "Open a session to add documents"}
        </p>
        <p className="text-[13px] text-muted">PDF, DOCX, TXT, Markdown, JSON</p>
      </div>
    </div>
  );
}
