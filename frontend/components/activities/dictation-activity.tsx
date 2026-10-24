"use client";

import { AudioPlayer } from "@/components/study";
import { speechText } from "@/lib/bilingual";
import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

export function DictationActivity({
  activity,
  response,
  onResponse,
  locked = false,
  languageCode = "",
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction } = useActivityCopy(activity, supportVisibility);
  const showText = activity.show_text === true;

  return (
    <div className="space-y-4">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      <p className="text-sm text-text-secondary">Ouça e escreva o que foi dito.</p>
      {activity.audio_text && (
        <AudioPlayer
          variant="compact"
          label="Ouvir"
          accessibleName="Ouvir o ditado"
          text={speechText(activity.audio_text)}
          languageCode={languageCode}
        />
      )}
      {showText && activity.audio_text && (
        <p className="font-medium text-text-primary">{activity.audio_text}</p>
      )}
      <textarea
        aria-label="Sua resposta"
        value={response}
        disabled={locked}
        onChange={(event) => onResponse(event.target.value)}
        rows={3}
        className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70"
        placeholder="Escreva o que ouviu"
      />
    </div>
  );
}
