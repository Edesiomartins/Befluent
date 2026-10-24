"use client";

import { AudioPlayer } from "@/components/study";
import { speechText } from "@/lib/bilingual";
import { choiceClass, useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";
import { AudioModelActivity } from "@/components/activities/audio-model-activity";

export function ChoiceActivity(props: ActivityRenderProps) {
  const { activity, response, onResponse, locked = false } = props;
  const { instruction, stimulus } = useActivityCopy(activity, props.supportVisibility);
  const options = activity.options ?? [];
  if (
    options.length === 0 &&
    activity.type === "recognition" &&
    !activity.vocabulary_item_id
  ) {
    return <AudioModelActivity {...props} />;
  }
  const groupLabel = instruction || "Opções da atividade";

  return (
    <div className="space-y-5">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {activity.show_text !== false && stimulus && (
        <p className="text-2xl font-semibold text-text-primary">{stimulus}</p>
      )}
      {activity.is_retry_variant && (
        <p className="text-xs text-text-secondary">
          Outra interação do mesmo objetivo. O idioma estudado continua o mesmo.
        </p>
      )}
      <div className="grid gap-2" role="radiogroup" aria-label={groupLabel}>
        {options.map((option) => {
          const selected = response === option;
          return (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={locked}
              onClick={() => {
                if (!locked) onResponse(option);
              }}
              className={choiceClass(selected, locked)}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function AudioChoiceActivity({
  activity,
  response,
  onResponse,
  locked = false,
  languageCode = "",
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction } = useActivityCopy(activity, supportVisibility);
  const groupLabel = instruction || "Opções da atividade de escuta";
  const showTranscript = activity.show_text === true;

  return (
    <div className="space-y-5">
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {activity.audio_text && (
        <AudioPlayer
          variant="compact"
          label="Ouvir"
          accessibleName={
            activity.audio_target_type === "example_sentence"
              ? "Ouvir frase de exemplo"
              : "Ouvir expressão"
          }
          text={speechText(activity.audio_text)}
          languageCode={languageCode}
        />
      )}
      {showTranscript && activity.prompt_target && (
        <p className="font-medium text-text-primary">{activity.prompt_target}</p>
      )}
      <div className="grid gap-2" role="radiogroup" aria-label={groupLabel}>
        {(activity.options ?? []).map((option) => {
          const selected = response === option;
          return (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={locked}
              onClick={() => {
                if (!locked) onResponse(option);
              }}
              className={choiceClass(selected, locked)}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}
