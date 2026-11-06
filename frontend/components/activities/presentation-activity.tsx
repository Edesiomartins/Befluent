"use client";

import { NoticingWhy } from "@/components/noticing-why";
import { AudioPlayer } from "@/components/study";
import { BilingualText } from "@/components/bilingual-text";
import { speechText } from "@/lib/bilingual";
import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

export function PresentationActivity({
  activity,
  languageCode = "",
  supportVisibility,
}: ActivityRenderProps) {
  const { gloss, instruction, visibility, nativeLanguage } = useActivityCopy(activity, supportVisibility);
  const termAudio = activity.audio_targets?.find(
    (target) => target.audio_target_type === "vocabulary_item",
  );
  const exampleAudio = activity.audio_targets?.find(
    (target) => target.audio_target_type === "example_sentence",
  );
  const exampleSupport = gloss(activity.example_translation, activity.example_translation_pt);

  return (
    <div className="space-y-6">
      {instruction && (
        <p lang={nativeLanguage || undefined} className="leading-7 text-text-secondary">{instruction}</p>
      )}
      <NoticingWhy why={gloss(activity.why_native, activity.why_pt)} examples={activity.examples} />
      <div>
        <p className="label">Expressão</p>
        <div className="mt-3 flex flex-wrap items-center gap-4">
          {activity.term && (
            <BilingualText
              heading
              target={activity.term}
              native={gloss(activity.translation, activity.translation_pt)}
              targetLang={languageCode}
              nativeLang={nativeLanguage}
              visibility={visibility}
              audio={
                termAudio?.audio_text ? (
                  <AudioPlayer
                    variant="compact"
                    accessibleName={`Ouvir expressão ${activity.term ?? ""}`.trim()}
                    text={speechText(termAudio.audio_text)}
                    languageCode={languageCode}
                  />
                ) : undefined
              }
            />
          )}
        </div>
        {activity.reading_or_pinyin && (
          <p className="mt-2 text-sm text-text-secondary">{activity.reading_or_pinyin}</p>
        )}
      </div>
      {activity.example_sentence && (
        <div className="border-t border-border pt-5">
          <p className="label">Frase de exemplo</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <p lang={languageCode || undefined} className="font-medium text-text-primary">{activity.example_sentence}</p>
            {exampleAudio?.audio_text && (
              <AudioPlayer
                variant="compact"
                accessibleName="Ouvir frase de exemplo"
                text={speechText(exampleAudio.audio_text)}
                languageCode={languageCode}
              />
            )}
          </div>
          {exampleSupport && (
            <p lang={nativeLanguage || undefined} className="mt-2 text-sm text-text-secondary">{exampleSupport}</p>
          )}
        </div>
      )}
    </div>
  );
}
