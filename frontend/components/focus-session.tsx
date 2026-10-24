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
  hideAction = false,
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
  hideAction?: boolean;
  onAction: () => void;
  children: ReactNode;
}) {
  const [confirming, setConfirming] = useState(false);
  const titleId = useId();
  const stayRef = useRef<HTMLButtonElement>(null);
  const safeMax = max > 0 ? max : 1;
  const pct = Math.min(100, Math.round((value / safeMax) * 100));

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
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-2xl flex-col px-5 pb-28 pt-5">
      <div className="flex items-center gap-3.5 rounded-xl border border-border bg-surface px-3.5 py-2 shadow-[0_1px_2px_rgba(15,23,42,0.03)]">
        <button
          type="button"
          className="min-h-9 shrink-0 rounded-lg px-2.5 text-xs font-semibold text-text-secondary transition-colors hover:bg-[var(--surface-soft)] hover:text-text-primary"
          onClick={() => setConfirming(true)}
        >
          Sair
        </button>
        <div
          className="h-2 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-elevated"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={safeMax}
          aria-valuenow={Math.min(value, safeMax)}
          aria-label={label}
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-200 motion-reduce:transition-none"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="shrink-0 text-xs font-semibold tabular-nums text-text-secondary" aria-hidden>
          {Math.min(value, safeMax)}/{safeMax}
        </span>
      </div>
      <div className="flex flex-1 flex-col justify-center py-8">{children}</div>
      {!hideAction && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface/95 px-5 py-3.5 pb-[max(0.85rem,env(safe-area-inset-bottom))] backdrop-blur-md">
          <div className="mx-auto max-w-2xl">
            <button
              type="button"
              className="min-h-13 w-full rounded-xl bg-primary text-base font-semibold text-white shadow-[0_1px_2px_rgba(15,23,42,0.14),inset_0_1px_0_rgba(255,255,255,0.18)] transition-colors hover:bg-[var(--primary-hover)] disabled:opacity-50"
              disabled={actionDisabled || loading}
              onClick={onAction}
            >
              {loading ? "Verificando…" : actionLabel}
            </button>
          </div>
        </div>
      )}
      {confirming && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-[#0b1220]/55 px-5 backdrop-blur-[2px]">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            className="panel w-full max-w-sm p-6 shadow-2xl"
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
                className="min-h-11 rounded-xl bg-primary text-sm font-semibold text-white shadow-[0_1px_2px_rgba(15,23,42,0.12)] hover:bg-[var(--primary-hover)]"
                onClick={() => setConfirming(false)}
              >
                Continuar estudando
              </button>
              <Link
                href={exitHref}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-border bg-surface text-sm font-semibold text-text-primary hover:bg-[var(--surface-soft)]"
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
