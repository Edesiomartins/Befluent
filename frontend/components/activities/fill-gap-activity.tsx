"use client";

import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

const fieldClass =
  "min-h-11 min-w-[8rem] rounded-lg border border-border bg-surface px-3 py-2 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70";

export function FillGapActivity({
  activity,
  response,
  onResponse,
  locked = false,
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction, stimulus } = useActivityCopy(activity, supportVisibility);
  const source = stimulus || activity.prompt || "";
  const parts = source.split("___");

  return (
    <div className="space-y-4">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {parts.length < 2 ? (
        <>
          {source && <p className="font-medium text-text-primary">{source}</p>}
          <textarea
            aria-label="Sua resposta"
            value={response}
            disabled={locked}
            onChange={(event) => onResponse(event.target.value)}
            rows={3}
            className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70"
          />
        </>
      ) : (
        <p className="text-lg leading-9 text-text-primary">
          {parts.map((part, index) => (
            <span key={`${part}-${index}`}>
              {part}
              {index < parts.length - 1 && (
                <input
                  aria-label={index === 0 ? "Sua resposta" : `Lacuna ${index + 1}`}
                  value={response.split(" | ")[index] ?? ""}
                  disabled={locked}
                  onChange={(event) => {
                    const gaps = response.split(" | ");
                    while (gaps.length < parts.length - 1) gaps.push("");
                    gaps[index] = event.target.value;
                    onResponse(gaps.slice(0, parts.length - 1).join(" | "));
                  }}
                  className={fieldClass}
                />
              )}
            </span>
          ))}
        </p>
      )}
    </div>
  );
}
