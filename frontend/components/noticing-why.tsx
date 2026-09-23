"use client";

import { useState } from "react";

export function NoticingWhy({
  why,
  examples = [],
}: {
  why?: string | null;
  examples?: string[];
}) {
  const [open, setOpen] = useState(false);
  const samples = examples.filter(Boolean).slice(0, 3);
  if (!why) return null;

  return (
    <div className="mt-4">
      <button
        type="button"
        className="text-sm font-semibold text-primary hover:underline"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? "Voltar à atividade" : "Por que esta forma?"}
      </button>
      {open && (
        <div className="mt-3 rounded-xl border border-border bg-surface-soft p-4 text-sm leading-6">
          <p>{why}</p>
          {samples.length > 0 && (
            <ul className="mt-3 space-y-1 text-text-secondary">
              {samples.map((example) => (
                <li key={example}>{example}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
