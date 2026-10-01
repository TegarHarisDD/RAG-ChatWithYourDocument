import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { SpinnerIcon } from "./icons";
import { btnDanger, btnGhost, btnPrimary, inputClass } from "../ui";

// A modal built on the native <dialog> element, so focus trapping, Escape, and
// the top-layer stacking come from the platform. A floating layer gets one soft
// diffuse shadow; everything else is flat.
export function Dialog({
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
      className="m-auto w-[min(92vw,28rem)] max-h-[85vh] overflow-auto rounded-panel bg-raised p-0 text-ink shadow-[0_8px_32px_oklch(0_0_0/0.08)]"
    >
      <div className="px-5 pb-3 pt-5">
        <h2 className="text-lg font-medium tracking-[-0.015em]">{title}</h2>
      </div>
      <div className="px-5 pb-4">{children}</div>
      <div className="flex justify-end gap-2 px-5 pb-5">{footer}</div>
    </dialog>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Delete",
  pendingLabel,
  danger = false,
  pending = false,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  pendingLabel?: string;
  danger?: boolean;
  pending?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      onClose={pending ? () => {} : onClose}
      title={title}
      footer={
        <>
          <button className={btnGhost} onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button
            className={danger ? btnDanger : btnPrimary}
            data-autofocus
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? (
              <>
                <SpinnerIcon />
                {pendingLabel ?? "Working…"}
              </>
            ) : (
              confirmLabel
            )}
          </button>
        </>
      }
    >
      {description ? <p className="text-sm text-muted">{description}</p> : null}
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
          <button type="submit" form={formId} className={btnPrimary} disabled={!trimmed}>
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
        <label className="flex flex-col gap-2 text-sm font-medium text-muted">
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
