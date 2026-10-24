"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Check, Lock } from "lucide-react";

export type TrailStep = {
  id: string;
  title: string;
  detail: string;
  meta?: string | null;
  badge?: string | null;
  state: "done" | "current" | "locked";
  href?: string;
};

const STATE_LABEL = {
  done: "Concluída",
  current: "Atual",
  locked: "Bloqueada",
} as const;

export function JourneyTrail({ steps }: { steps: TrailStep[] }) {
  const currentIndex = Math.max(0, steps.findIndex((step) => step.state === "current"));
  const [focusIndex, setFocusIndex] = useState(currentIndex);
  const moved = useRef(false);
  const items = useRef<Array<HTMLAnchorElement | HTMLButtonElement | null>>([]);

  useEffect(() => {
    if (!moved.current) return;
    items.current[focusIndex]?.focus();
  }, [focusIndex]);

  function onKeyDown(event: KeyboardEvent) {
    const next =
      event.key === "ArrowDown" || event.key === "ArrowRight"
        ? 1
        : event.key === "ArrowUp" || event.key === "ArrowLeft"
          ? -1
          : 0;
    if (!next) return;
    event.preventDefault();
    moved.current = true;
    setFocusIndex((index) => Math.min(steps.length - 1, Math.max(0, index + next)));
  }

  if (steps.length === 0) return null;

  return (
    <ol
      aria-label="Trilha do cronograma"
      className="grid"
      onKeyDown={onKeyDown}
    >
      {steps.map((step, index) => {
        const locked = step.state === "locked";
        const className = `min-h-12 w-full rounded-xl border px-4 py-3 text-left transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary ${
          step.state === "current"
            ? "border-primary/45 bg-primary-soft/40 shadow-[0_1px_2px_rgba(37,99,235,0.08)]"
            : step.state === "done"
              ? "border-border bg-surface hover:bg-[var(--surface-soft)]"
              : "border-transparent bg-transparent hover:bg-[var(--surface-soft)]/60"
        }`;
        const body = (
          <span className="flex flex-wrap items-center justify-between gap-2">
            <span>
              <span className="block text-sm font-semibold text-text-primary">{step.title}</span>
              <span className="mt-0.5 block text-sm text-text-secondary">{step.detail}</span>
            </span>
            <span className="flex items-center gap-1.5 text-xs font-semibold">
              <span
                className={`rounded-full px-2.5 py-0.5 ${
                  step.state === "done"
                    ? "bg-[var(--success-soft)] text-success"
                    : step.state === "current"
                      ? "bg-primary text-white"
                      : "bg-[var(--surface-elevated)] text-text-secondary"
                }`}
              >
                {STATE_LABEL[step.state]}
              </span>
              {step.meta ? <span className="tech-badge">{step.meta}</span> : null}
              {step.badge ? (
                <span className="rounded-full bg-[var(--streak-soft)] px-2.5 py-0.5 text-xs font-semibold text-streak">
                  {step.badge}
                </span>
              ) : null}
            </span>
          </span>
        );
        return (
          <li key={step.id} className="relative flex gap-4 pb-3.5 last:pb-0">
            {index < steps.length - 1 && (
              <span
                aria-hidden
                className={`absolute top-9 left-[0.82rem] h-[calc(100%-1.25rem)] w-px ${
                  step.state === "done" ? "bg-success/50" : "bg-border"
                }`}
              />
            )}
            <span
              aria-hidden
              className={`relative z-10 mt-3.5 grid size-7 shrink-0 place-items-center rounded-full border-2 text-xs font-semibold ${
                step.state === "done"
                  ? "border-success bg-success text-white"
                  : step.state === "current"
                    ? "border-primary bg-primary text-white shadow-[0_0_0_4px_rgba(37,99,235,0.15)]"
                    : "border-border bg-surface text-text-secondary"
              }`}
            >
              {step.state === "done" ? (
                <Check className="size-3.5" />
              ) : step.state === "locked" ? (
                <Lock className="size-3" />
              ) : (
                index + 1
              )}
            </span>
            {step.href && step.state === "current" ? (
              <Link
                ref={(node) => {
                  items.current[index] = node;
                }}
                href={step.href}
                aria-current="step"
                tabIndex={focusIndex === index ? 0 : -1}
                className={className}
              >
                {body}
              </Link>
            ) : (
              <button
                ref={(node) => {
                  items.current[index] = node;
                }}
                type="button"
                aria-disabled={locked || undefined}
                aria-current={step.state === "current" ? "step" : undefined}
                tabIndex={focusIndex === index ? 0 : -1}
                className={className}
                onClick={(event) => {
                  if (locked) event.preventDefault();
                }}
              >
                {body}
              </button>
            )}
          </li>
        );
      })}
    </ol>
  );
}
