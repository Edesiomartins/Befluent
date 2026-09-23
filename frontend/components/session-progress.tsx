"use client";

import { Check } from "lucide-react";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

export type SessionAreaProgress = {
  key: string;
  label: string;
  completed: number;
  total: number;
};

export function SessionProgress({
  completed,
  total,
  percent,
  currentLabel,
  nextLabel,
  justCompleted = false,
  areas = [],
}: {
  completed: number;
  total: number;
  percent: number;
  currentLabel?: string | null;
  nextLabel?: string | null;
  justCompleted?: boolean;
  areas?: SessionAreaProgress[];
}) {
  const reduced = usePrefersReducedMotion();
  if (total <= 0) return null;
  const width = Math.max(0, Math.min(100, percent));

  return (
    <div className="mb-4" aria-live="polite">
      <div className="flex items-center justify-between gap-3 text-xs text-text-secondary">
        <p>
          <span className="font-semibold text-text-primary">
            Aula de hoje · {completed} / {total}
          </span>
          {currentLabel ? ` · ${currentLabel}` : ""}
        </p>
        <p className="tabular-nums">{width}%</p>
      </div>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-soft"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={width}
        aria-label="Progresso da sessão"
      >
        <div
          className={`h-full rounded-full bg-primary ${reduced ? "" : "session-bar-fill"}`}
          style={{ width: `${width}%` }}
        />
      </div>
      {areas.length > 0 && (
        <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {areas.map((area) => {
            const done = area.completed >= area.total && area.total > 0;
            return (
              <li
                key={area.key}
                className="rounded-lg bg-surface-soft px-2.5 py-2 text-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-text-secondary">{area.label}</span>
                  {done ? (
                    <Check className="size-3.5 shrink-0 text-primary" aria-label="concluído" />
                  ) : (
                    <span className="tabular-nums text-text-primary">
                      {area.completed}/{area.total}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <div className="mt-2 flex items-center justify-between gap-3 text-xs text-text-secondary">
        <p>{nextLabel ? `Próxima: ${nextLabel}` : "Última atividade desta sessão"}</p>
        {justCompleted && (
          <span className={`inline-flex items-center gap-1 text-primary ${reduced ? "" : "session-check"}`}>
            <Check className="size-3.5" aria-hidden />
            Concluída
          </span>
        )}
      </div>
    </div>
  );
}
