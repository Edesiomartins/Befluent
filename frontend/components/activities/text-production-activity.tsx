"use client";

import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

const fieldClass =
  "w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70";

export function TextProductionActivity({
  activity,
  response,
  onResponse,
  locked = false,
  supportVisibility,
  heading,
}: ActivityRenderProps & { heading: string }) {
  const { gloss, instruction, stimulus } = useActivityCopy(activity, supportVisibility);
  const help = gloss(activity.scaffold_native, activity.scaffold_pt);

  return (
    <div className="space-y-4">
      <p className="label">{heading}</p>
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {stimulus && <p className="text-lg font-semibold text-text-primary">{stimulus}</p>}
      {help && (
        <details className="disclosure rounded-lg border border-border px-4 py-3 text-sm">
          <summary className="cursor-pointer font-semibold text-primary">Ver ajuda</summary>
          <p className="mt-3 leading-6 text-text-secondary">{help}</p>
        </details>
      )}
      <textarea
        aria-label="Sua resposta"
        value={response}
        disabled={locked}
        onChange={(event) => onResponse(event.target.value)}
        rows={4}
        className={fieldClass}
        placeholder="Sua resposta"
      />
    </div>
  );
}

export function GuidedInputActivity(props: ActivityRenderProps) {
  return <TextProductionActivity {...props} heading="Produção guiada" />;
}

export function OpenInputActivity(props: ActivityRenderProps) {
  return <TextProductionActivity {...props} heading="Produção" />;
}
