"use client";

import { useEffect, useMemo, useState } from "react";
import { displayOrder } from "@/lib/display-order";
import { choiceClass, useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

type Side = { id: number; text: string };

export function MatchingActivity({
  activity,
  response,
  onResponse,
  locked = false,
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction, gloss } = useActivityCopy(activity, supportVisibility);
  const pairs = useMemo(() => activity.pairs ?? [], [activity.pairs]);
  const left = useMemo<Side[]>(
    () => pairs.map((pair, id) => ({ id, text: pair.term })),
    [pairs],
  );
  const rightOrder = useMemo(
    () => displayOrder(pairs.length, pairs.map((pair) => pair.term).join("|")),
    [pairs],
  );
  const right = rightOrder.map((id) => ({
    id,
    text: gloss(pairs[id]?.hint, pairs[id]?.hint_pt) || pairs[id]?.term || "",
  }));
  const [activeLeft, setActiveLeft] = useState<number | null>(null);
  const [matched, setMatched] = useState<Array<{ left: number; right: number }>>([]);

  useEffect(() => {
    if (!response) {
      setMatched([]);
      setActiveLeft(null);
    }
  }, [response]);

  const usedLeft = new Set(matched.map((item) => item.left));
  const usedRight = new Set(matched.map((item) => item.right));

  function chooseRight(rightId: number) {
    if (locked || activeLeft == null || usedRight.has(rightId)) return;
    const next = [...matched, { left: activeLeft, right: rightId }];
    setMatched(next);
    setActiveLeft(null);
    onResponse(
      next
        .map((item) => {
          const term = left.find((entry) => entry.id === item.left)?.text ?? "";
          const hint = right.find((entry) => entry.id === item.right)?.text ?? "";
          return `${term} = ${hint}`;
        })
        .join("\n"),
    );
  }

  return (
    <div className="space-y-4">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      <p className="text-sm text-text-secondary">
        Selecione um item e depois o correspondente. Os pares certos não aparecem prontos.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div role="group" aria-label="Itens">
          {left.map((item) => {
            const done = usedLeft.has(item.id);
            return (
              <button
                key={item.id}
                type="button"
                disabled={locked || done}
                aria-pressed={activeLeft === item.id}
                className={`mb-2 w-full ${choiceClass(activeLeft === item.id || done, locked || done)}`}
                onClick={() => setActiveLeft(item.id)}
              >
                {item.text}
              </button>
            );
          })}
        </div>
        <div role="group" aria-label="Correspondentes">
          {right.map((item) => {
            const done = usedRight.has(item.id);
            return (
              <button
                key={`${item.id}-${item.text}`}
                type="button"
                disabled={locked || done || activeLeft == null}
                className={`mb-2 w-full ${choiceClass(done, locked || done || activeLeft == null)}`}
                onClick={() => chooseRight(item.id)}
              >
                {item.text}
              </button>
            );
          })}
        </div>
      </div>
      {matched.length > 0 && (
        <p className="text-sm text-text-secondary" role="status">
          {matched.length} de {pairs.length} associados.
        </p>
      )}
    </div>
  );
}
