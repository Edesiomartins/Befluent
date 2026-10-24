"use client";

import { AudioPlayer, Recorder } from "@/components/study";
import { speechText } from "@/lib/bilingual";
import { TargetLine } from "@/components/bilingual-text";
import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

const TITLES: Record<string, string> = {
  speech_repeat: "Repita",
  speech_shadow: "Acompanhe em voz alta",
  speech_retell: "Reconte",
  repeat: "Repita",
  shadow: "Acompanhe em voz alta",
  retell: "Reconte",
};

export function SpeechActivity({
  activity,
  response,
  onResponse,
  locked = false,
  languageCode = "",
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction, stimulus } = useActivityCopy(activity, supportVisibility);
  const title =
    TITLES[activity.interaction_family ?? ""] ||
    TITLES[activity.type] ||
    "Fale";
  const model = stimulus || activity.audio_text || "";

  return (
    <div className="space-y-4">
      <p className="label">{title}</p>
      {instruction && <p className="border-b border-border pb-3 text-sm leading-6 text-text-secondary">{instruction}</p>}
      {model && (
        <TargetLine
          text={model}
          audio={
            activity.audio_text ? (
              <AudioPlayer
                variant="compact"
                label="Ouvir modelo"
                accessibleName="Ouvir o modelo"
                text={speechText(activity.audio_text)}
                languageCode={languageCode}
              />
            ) : undefined
          }
        />
      )}
      <Recorder onTranscript={onResponse} languageCode={languageCode} />
      {response && (
        <p className="text-sm text-text-secondary" role="status">
          Transcrição: <span className="font-medium text-text-primary">{response}</span>
        </p>
      )}
      <textarea
        aria-label="Sua resposta"
        value={response}
        disabled={locked}
        onChange={(event) => onResponse(event.target.value)}
        rows={3}
        className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70"
        placeholder="Ou escreva o que disse"
      />
    </div>
  );
}
