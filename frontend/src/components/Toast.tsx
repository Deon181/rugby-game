import { useCallback, useEffect, useMemo, useState, createContext, useContext } from "react";
import type { ReactNode } from "react";

type ToastLevel = "info" | "success" | "warn" | "error";

type Toast = {
  id: number;
  message: string;
  level: ToastLevel;
};

type ToastContextValue = {
  toast: (message: string, level?: ToastLevel) => void;
};

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 0;

const levelStyles: Record<ToastLevel, string> = {
  info: "border-sky-400/30 bg-sky-400/15 text-sky-100",
  success: "border-emerald-400/30 bg-emerald-400/15 text-emerald-100",
  warn: "border-amber-400/30 bg-amber-400/15 text-amber-100",
  error: "border-rose-400/30 bg-rose-400/15 text-rose-100",
};

const levelIcons: Record<ToastLevel, string> = {
  info: "i",
  success: "\u2713",
  warn: "!",
  error: "\u2717",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((message: string, level: ToastLevel = "info") => {
    const id = ++nextId;
    setToasts((prev) => [...prev, { id, message, level }]);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = window.setTimeout(() => onDismiss(toast.id), 4000);
    return () => window.clearTimeout(timer);
  }, [toast.id, onDismiss]);

  return (
    <div
      className={`flex items-center gap-3 rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-md animate-in slide-in-from-right ${levelStyles[toast.level]}`}
      style={{ minWidth: 280, maxWidth: 420, animation: "slideIn 0.3s ease-out" }}
    >
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-bold">
        {levelIcons[toast.level]}
      </span>
      <span className="text-sm font-medium">{toast.message}</span>
      <button className="ml-auto shrink-0 text-xs opacity-60 hover:opacity-100" onClick={() => onDismiss(toast.id)}>
        Close
      </button>
    </div>
  );
}
