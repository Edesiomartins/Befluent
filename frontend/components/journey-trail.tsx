"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

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
        const className = `min-h-11 rounded-xl px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary ${
          step.state === "current" ? "bg-primary-soft/50" : ""
        }`;
        const body = (
          <>
            <span className="block text-sm font-semibold text-text-primary">{step.title}</span>
            <span className="mt-0.5 block text-sm text-text-secondary">{step.detail}</span>
            <span className="mt-1 block text-xs font-semibold">
              <span className={step.state === "done" ? "text-success" : step.state === "current" ? "text-primary" : "text-text-secondary"}>
                {STATE_LABEL[step.state]}
              </span>
              {step.meta ? <span className="ml-2 text-text-secondary">{step.meta}</span> : null}
              {step.badge ? <span className="ml-2 text-text-secondary">{step.badge}</span> : null}
            </span>
          </>
        );
        return (
          <li key={step.id} className="relative flex gap-4 pb-5">
            {index < steps.length - 1 && (
              <span aria-hidden className="absolute top-8 left-[0.7rem] h-[calc(100%-1.25rem)] w-px bg-border" />
            )}
            <span
              aria-hidden
              className={`relative z-10 mt-3 size-6 shrink-0 rounded-full border-2 ${
                step.state === "done"
                  ? "border-success bg-success"
                  : step.state === "current"
                    ? "border-primary bg-primary"
                    : "border-border bg-surface"
              }`}
            />
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
