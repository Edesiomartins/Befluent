"use client";

import { NoticingWhy } from "@/components/noticing-why";
import { BilingualText } from "@/components/bilingual-text";
import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

/** Modelo para ouvir ou observar. Não pede digitação. */
export function AudioModelActivity({ activity, supportVisibility }: ActivityRenderProps) {
  const { gloss, instruction, visibility } = useActivityCopy(activity, supportVisibility);
  const lines = activity.models ?? activity.examples ?? [];

  return (
    <div className="space-y-4">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      <NoticingWhy why={gloss(activity.why_native, activity.why_pt)} examples={activity.examples} />
      {activity.title ? (
        <BilingualText
          target={activity.title_target || activity.title}
          native={gloss(activity.title_native, activity.title_pt)}
          visibility={visibility}
        />
      ) : (
        gloss(activity.title_native, activity.title_pt) && (
          <p className="text-lg font-semibold text-text-primary">
            {gloss(activity.title_native, activity.title_pt)}
          </p>
        )
      )}
      {activity.can_do && (
        <p className="rounded-xl bg-surface-elevated px-4 py-3 text-sm leading-6 text-text-primary">
          {activity.can_do}
        </p>
      )}
      {lines.length > 0 && (
        <ul className="space-y-2">
          {lines.map((line) => (
            <li
              key={line}
              className="rounded-xl border border-border bg-surface px-4 py-3 font-medium text-text-primary"
            >
              {line}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
