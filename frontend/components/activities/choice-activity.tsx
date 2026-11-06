"use client";

import { useRef } from "react";
import { AudioPlayer } from "@/components/study";
import { speechText } from "@/lib/bilingual";
import { TargetLine } from "@/components/bilingual-text";
import { choiceClass, useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";
import { AudioModelActivity } from "@/components/activities/audio-model-activity";

const RADIO_KEYS = ["ArrowDown", "ArrowUp", "ArrowRight", "ArrowLeft"];

export function ChoiceOptions({
  options,
  response,
  onResponse,
  locked,
  label,
}: {
  options: string[];
  response: string;
  onResponse: (value: string) => void;
  locked: boolean;
  label: string;
}) {
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  return (
    <div className="grid gap-2" role="radiogroup" aria-label={label}>
      {options.map((option, index) => {
        const selected = response === option;
        const tabIndex = selected || (!response && index === 0) ? 0 : -1;
        return (
          <button
            key={option}
            ref={(node) => {
              refs.current[index] = node;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={tabIndex}
            disabled={locked}
            onClick={() => {
              if (!locked) onResponse(option);
            }}
            onKeyDown={(event) => {
              if (locked || !RADIO_KEYS.includes(event.key) || options.length === 0) return;
              event.preventDefault();
              const delta = event.key === "ArrowDown" || event.key === "ArrowRight" ? 1 : -1;
              const next = (index + delta + options.length) % options.length;
              onResponse(options[next]);
              refs.current[next]?.focus();
            }}
            className={choiceClass(selected, locked)}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

export function ChoiceActivity(props: ActivityRenderProps) {
  const { activity, response, onResponse, locked = false } = props;
  const { instruction, stimulus, nativeLanguage } = useActivityCopy(activity, props.supportVisibility);
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
      {instruction && (
        <p lang={nativeLanguage || undefined} className="border-b border-border pb-3 text-sm leading-6 text-text-secondary">{instruction}</p>
      )}
      {activity.show_text !== false && stimulus && (
        <TargetLine
          lang={props.languageCode}
          text={stimulus}
          audio={
            activity.audio_text ? (
              <AudioPlayer
                variant="compact"
                accessibleName={`Ouvir ${stimulus}`}
                text={speechText(activity.audio_text)}
                languageCode={props.languageCode}
              />
            ) : undefined
          }
        />
      )}
      {activity.is_retry_variant && (
        <p className="text-xs text-text-secondary">
          Outra interação do mesmo objetivo. O idioma estudado continua o mesmo.
        </p>
      )}
      <ChoiceOptions
        options={options}
        response={response}
        onResponse={onResponse}
        locked={locked}
        label={groupLabel}
      />
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
  const { instruction, nativeLanguage } = useActivityCopy(activity, supportVisibility);
  const groupLabel = instruction || "Opções da atividade de escuta";
  const showTranscript = activity.show_text === true;

  return (
    <div className="space-y-5">
      {instruction && (
        <p lang={nativeLanguage || undefined} className="border-b border-border pb-3 text-sm leading-6 text-text-secondary">{instruction}</p>
      )}
      <div className="flex items-start gap-3">
        {showTranscript && activity.prompt_target && (
          <p lang={languageCode || undefined} className="min-w-0 flex-1 text-xl font-medium leading-8 text-text-primary">{activity.prompt_target}</p>
        )}
        {activity.audio_text && (
          <div className="shrink-0">
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
          </div>
        )}
      </div>
      <ChoiceOptions
        options={activity.options ?? []}
        response={response}
        onResponse={onResponse}
        locked={locked}
        label={groupLabel}
      />
    </div>
  );
}
