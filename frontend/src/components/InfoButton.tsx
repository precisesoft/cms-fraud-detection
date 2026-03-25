import React from "react";
import { Info, X } from "lucide-react";

interface InfoButtonProps {
  title: string;
  children: React.ReactNode;
}

export function InfoButton({ title, children }: InfoButtonProps) {
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const titleId = React.useId();

  const close = React.useCallback(() => {
    setOpen(false);
    triggerRef.current?.focus();
  }, []);

  React.useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, close]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="dialog"
        aria-label={`Info: ${title}`}
        onClick={() => setOpen(true)}
        className="inline-flex items-center justify-center rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <Info size={14} className="text-slate-400 hover:text-indigo-500" />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={close}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="relative mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <h2 id={titleId} className="text-base font-semibold text-slate-800">
                {title}
              </h2>
              <button
                type="button"
                aria-label="Close"
                onClick={close}
                className="rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              >
                <X size={16} className="text-slate-500 hover:text-slate-800" />
              </button>
            </div>
            <div className="mt-3 text-sm text-slate-600">{children}</div>
          </div>
        </div>
      )}
    </>
  );
}
