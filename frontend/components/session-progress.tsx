"use client";

import { Check } from "lucide-react";
import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

export function SessionProgress({
  completed,
  total,
  percent,
  currentLabel,
  nextLabel,
  justCompleted = false,
}: {
  completed: number;
  total: number;
  percent: number;
  currentLabel?: string | null;
  nextLabel?: string | null;
  justCompleted?: boolean;
}) {
  const reduced = usePrefersReducedMotion();
  if (total <= 0) return null;
  const width = Math.max(0, Math.min(100, percent));

  return (
    <div className="mb-4" aria-live="polite">
      <div className="flex items-center justify-between gap-3 text-xs text-text-secondary">
        <p>
          <span className="font-semibold text-text-primary">
            {completed} de {total} atividades
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
      <div className="mt-2 flex items-center justify-between gap-3 text-xs text-text-secondary">
        <p>{nextLabel ? `Próxima: ${nextLabel}` : "Última atividade deste bloco"}</p>
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
