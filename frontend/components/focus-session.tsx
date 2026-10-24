"use client";

import Link from "next/link";
import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";

const FocusSessionContext = createContext<{
  active: boolean;
  setActive: (active: boolean) => void;
}>({ active: false, setActive: () => {} });

export function FocusSessionProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  return (
    <FocusSessionContext.Provider value={{ active, setActive }}>
      {children}
    </FocusSessionContext.Provider>
  );
}

export function useFocusSession() {
  return useContext(FocusSessionContext);
}

export function FocusFrame({
  value,
  max,
  label,
  exitHref = "/dashboard",
  actionLabel,
  actionDisabled = false,
  loading = false,
  onAction,
  children,
}: {
  value: number;
  max: number;
  label: string;
  exitHref?: string;
  actionLabel: string;
  actionDisabled?: boolean;
  loading?: boolean;
  onAction: () => void;
  children: ReactNode;
}) {
  const [confirming, setConfirming] = useState(false);
  const titleId = useId();
  const stayRef = useRef<HTMLButtonElement>(null);
  const safeMax = max > 0 ? max : 1;

  useEffect(() => {
    if (!confirming) return;
    stayRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setConfirming(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [confirming]);

  return (
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-xl flex-col px-5 pb-28 pt-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="min-h-11 shrink-0 rounded-xl px-2 text-sm font-semibold text-text-secondary hover:text-primary"
          onClick={() => setConfirming(true)}
        >
          Sair
        </button>
        <div
          className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-elevated"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={safeMax}
          aria-valuenow={Math.min(value, safeMax)}
          aria-label={label}
        >
          <div
            className="h-full rounded-full bg-primary"
            style={{ width: `${Math.min(100, Math.round((value / safeMax) * 100))}%` }}
          />
        </div>
      </div>
      <div className="flex flex-1 flex-col justify-center py-8">{children}</div>
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface px-5 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <div className="mx-auto max-w-xl">
          <button
            type="button"
            className="min-h-14 w-full rounded-2xl bg-primary text-lg font-semibold text-white hover:bg-[var(--primary-hover)] disabled:opacity-50"
            disabled={actionDisabled || loading}
            onClick={onAction}
          >
            {loading ? "Verificando…" : actionLabel}
          </button>
        </div>
      </div>
      {confirming && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-[var(--text-primary)]/40 px-5">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="w-full max-w-sm rounded-2xl bg-surface p-6 shadow-xl"
          >
            <h2 id={titleId} className="text-lg font-semibold text-text-primary">
              Sair desta sessão?
            </h2>
            <p className="mt-2 text-sm leading-6 text-text-secondary">
              O que você já concluiu permanece salvo.
            </p>
            <div className="mt-5 grid gap-2">
              <button
                ref={stayRef}
                type="button"
                className="min-h-11 rounded-xl bg-primary font-semibold text-white"
                onClick={() => setConfirming(false)}
              >
                Continuar estudando
              </button>
              <Link
                href={exitHref}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-border font-semibold text-text-primary"
              >
                Sair
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
