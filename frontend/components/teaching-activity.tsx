"use client";

import type { ComponentType } from "react";
import { AudioChoiceActivity, ChoiceActivity } from "@/components/activities/choice-activity";
import { AudioModelActivity } from "@/components/activities/audio-model-activity";
import { DictationActivity } from "@/components/activities/dictation-activity";
import { FillGapActivity } from "@/components/activities/fill-gap-activity";
import { MatchingActivity } from "@/components/activities/matching-activity";
import {
  DialogueActivity,
  TransferActivity,
  UnsupportedActivity,
} from "@/components/activities/mission-activity";
import { PresentationActivity } from "@/components/activities/presentation-activity";
import { RecallActivity } from "@/components/activities/recall-activity";
import { SpeechActivity } from "@/components/activities/speech-activity";
import {
  GuidedInputActivity,
  OpenInputActivity,
} from "@/components/activities/text-production-activity";
import { WordOrderActivity } from "@/components/activities/word-order-activity";
import type { ActivityRenderProps } from "@/components/activities/activity-props";
import { resolveInteractionFamily } from "@/lib/activity-registry";
import { ActivityFeedback } from "@/components/activities/activity-feedback";
import type { AnswerFeedback } from "@/types/teaching";

export function TeachingAnswerFeedback({
  feedback,
  sameObjectiveRetry = true,
  showRetryNote = true,
}: {
  feedback: AnswerFeedback | null | undefined;
  sameObjectiveRetry?: boolean;
  showRetryNote?: boolean;
}) {
  return (
    <ActivityFeedback
      feedback={feedback}
      sameObjectiveRetry={sameObjectiveRetry}
      showRetryNote={showRetryNote}
    />
  );
}

const RENDERERS: Record<string, ComponentType<ActivityRenderProps>> = {
  presentation: PresentationActivity,
  choice: ChoiceActivity,
  audio_choice: AudioChoiceActivity,
  audio_model: AudioModelActivity,
  inline_gap: FillGapActivity,
  tap_order: WordOrderActivity,
  pair_match: MatchingActivity,
  recall: RecallActivity,
  guided_input: GuidedInputActivity,
  open_input: OpenInputActivity,
  speech_repeat: SpeechActivity,
  speech_shadow: SpeechActivity,
  speech_retell: SpeechActivity,
  dialogue: DialogueActivity,
  transfer: TransferActivity,
  dictation: DictationActivity,
};

export function TeachingActivityBody(props: ActivityRenderProps) {
  const family = resolveInteractionFamily(props.activity);
  const Renderer = RENDERERS[family];
  if (!Renderer) {
    if (family === "unspecified") return <OpenInputActivity {...props} />;
    return <UnsupportedActivity />;
  }
  return (
    <div data-interaction-family={family}>
      <Renderer {...props} />
    </div>
  );
}
