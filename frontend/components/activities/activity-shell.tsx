"use client";

import type { ReactNode } from "react";
import { teachingPhaseLabel } from "@/lib/teaching-phase-label";

export const ACTIVITY_FOCUS_ID = "atividade-atual";

export function focusCurrentActivity() {
  const node = document.getElementById(ACTIVITY_FOCUS_ID);
  if (node instanceof HTMLElement) node.focus();
}

export function ActivityShell({
  phase,
  phaseLabel,
  area,
  languageLabel,
  level,
  step,
  total,
  objective,
  children,
  showPhase = true,
  footer,
}: {
  phase?: string | null;
  phaseLabel?: string | null;
  area?: string | null;
  languageLabel?: string | null;
  level?: string | null;
  step?: number | null;
  total?: number | null;
  objective?: string | null;
  showPhase?: boolean;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const label = teachingPhaseLabel(phase, phaseLabel);
  const meta = [languageLabel, level, area].filter(Boolean).join(" · ");
  const position =
    step != null && total != null && total > 0 ? `${step} / ${total}` : null;

  return (
    <section
      id={ACTIVITY_FOCUS_ID}
      tabIndex={-1}
      className="mx-auto w-full max-w-3xl outline-none focus-visible:ring-2 focus-visible:ring-primary"
      aria-label="Atividade"
    >
      <header className="mb-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="label">{showPhase ? label : "Atividade"}</p>
          {position && <p className="text-sm tabular-nums text-text-secondary">{position}</p>}
        </div>
        {meta && <p className="mt-1 text-sm text-text-secondary">{meta}</p>}
        {objective && <p className="mt-2 text-sm leading-6 text-text-primary">{objective}</p>}
      </header>
      {children}
      {footer && <div className="mt-4">{footer}</div>}
    </section>
  );
}

export function ActivityEmpty({
  label = "Nenhuma atividade neste momento.",
}: {
  label?: string;
}) {
  return (
    <p role="status" className="text-sm leading-6 text-text-secondary">
      {label}
    </p>
  );
}
