import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { btnDanger, btnGhost, btnPrimary, inputClass } from "../ui";

// A modal built on the native <dialog> element, so focus trapping, Escape, and
// the top-layer stacking come from the platform. Only the chrome is ours.
function Dialog({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) {
      el.showModal();
      el.querySelector<HTMLElement>("[data-autofocus]")?.focus();
    } else if (!open && el.open) {
      el.close();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className="m-auto w-[min(92vw,28rem)] max-h-[85vh] overflow-auto border border-line bg-raised p-0 text-ink shadow-[0_24px_60px_-20px_rgba(12,18,28,0.55)] ring-1 ring-black/5 dark:ring-white/10"
    >
      <div className="border-b border-line px-5 py-3">
        <h2 className="font-display text-lg font-medium">{title}</h2>
      </div>
      <div className="px-5 py-4">{children}</div>
      <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>
    </dialog>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Delete",
  danger = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <button className={btnGhost} onClick={onClose}>
            Cancel
          </button>
          <button
            className={danger ? btnDanger : btnPrimary}
            data-autofocus
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      {description ? (
        <p className="font-reading text-sm leading-relaxed text-muted">{description}</p>
      ) : null}
    </Dialog>
  );
}

export function PromptDialog({
  open,
  title,
  label,
  initialValue,
  confirmLabel = "Save",
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  label: string;
  initialValue: string;
  confirmLabel?: string;
  onConfirm: (value: string) => void;
  onClose: () => void;
}) {
  const formId = useId();
  const [value, setValue] = useState(initialValue);

  useEffect(() => {
    if (open) setValue(initialValue);
  }, [open, initialValue]);

  const trimmed = value.trim();

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={title}
      footer={
        <>
          <button type="button" className={btnGhost} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form={formId}
            className={btnPrimary}
            disabled={!trimmed}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <form
        id={formId}
        onSubmit={(event) => {
          event.preventDefault();
          if (trimmed) onConfirm(trimmed);
        }}
      >
        <label className="flex flex-col gap-2 font-mono text-[11px] tracking-wide text-muted">
          {label}
          <input
            className={inputClass}
            value={value}
            data-autofocus
            onChange={(event) => setValue(event.target.value)}
          />
        </label>
      </form>
    </Dialog>
  );
}
