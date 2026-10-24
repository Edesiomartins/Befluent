"use client";

import { useEffect, useMemo, useState } from "react";
import { displayOrder } from "@/lib/display-order";
import { choiceClass, focusSiblingButton, useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

export function WordOrderActivity({
  activity,
  response,
  onResponse,
  locked = false,
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction } = useActivityCopy(activity, supportVisibility);
  const tokens = activity.tokens ?? [];
  const seed = `${activity.index ?? ""}:${tokens.join("|")}`;
  const bank = useMemo(() => displayOrder(tokens.length, seed), [seed, tokens.length]);
  const [picked, setPicked] = useState<number[]>([]);

  useEffect(() => {
    if (!response) setPicked([]);
  }, [response]);

  function commit(next: number[]) {
    setPicked(next);
    onResponse(next.map((index) => tokens[index] ?? "").join(" "));
  }

  const used = new Set(picked);

  return (
    <div className="space-y-4">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {tokens.length === 0 ? (
        <p role="status" className="text-sm text-text-secondary">
          Esta atividade não trouxe as palavras para ordenar.
        </p>
      ) : (
        <>
          <div
            className="min-h-16 rounded-xl border border-dashed border-border bg-surface-soft px-3 py-3"
            aria-label="Frase em construção"
            tabIndex={0}
            onKeyDown={(event) => {
              if (locked) return;
              if (event.key === "Backspace") {
                event.preventDefault();
                commit(picked.slice(0, -1));
              }
            }}
          >
            {picked.length === 0 ? (
              <p className="text-sm text-text-secondary">Toque as palavras na ordem da frase.</p>
            ) : (
              <ol className="flex flex-wrap gap-2">
                {picked.map((index, position) => (
                  <li key={`${index}-${position}`}>
                    <button
                      type="button"
                      disabled={locked}
                      className={choiceClass(true, locked)}
                      onClick={() => {
                        if (!locked) commit(picked.filter((_, item) => item !== position));
                      }}
                    >
                      {tokens[index]}
                      <span className="sr-only">, remover</span>
                    </button>
                  </li>
                ))}
              </ol>
            )}
          </div>
          <div
            className="flex flex-wrap gap-2"
            role="group"
            aria-label="Palavras disponíveis"
            onKeyDown={focusSiblingButton}
          >
            {bank.map((index) =>
              used.has(index) ? null : (
                <button
                  key={index}
                  type="button"
                  disabled={locked}
                  className={choiceClass(false, locked)}
                  onClick={() => {
                    if (!locked) commit([...picked, index]);
                  }}
                >
                  {tokens[index]}
                </button>
              ),
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="min-h-11 rounded-lg px-3 text-sm font-semibold text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary"
              disabled={locked || picked.length === 0}
              onClick={() => commit(picked.slice(0, -1))}
            >
              Desfazer
            </button>
            <button
              type="button"
              className="min-h-11 rounded-lg px-3 text-sm font-semibold text-text-secondary outline-none focus-visible:ring-2 focus-visible:ring-primary"
              disabled={locked || picked.length === 0}
              onClick={() => commit([])}
            >
              Recomeçar
            </button>
          </div>
        </>
      )}
    </div>
  );
}
