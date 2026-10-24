"use client";

import type { TeachingActivity } from "@/types/teaching";
import { supportText } from "@/lib/bilingual";
import { useLearnerNativeLanguage } from "@/components/native-language-context";

export type ActivityRenderProps = {
  activity: TeachingActivity;
  response: string;
  onResponse: (value: string) => void;
  locked?: boolean;
  languageCode?: string;
  supportVisibility?: string | null;
};

export function useActivityCopy(
  activity: TeachingActivity,
  supportVisibility?: string | null,
) {
  const nativeLanguage = useLearnerNativeLanguage();
  const gloss = (native?: string | null, legacy?: string | null) =>
    supportText({ nativeLanguage, native, legacyPortuguese: legacy });
  const instruction = supportText({
    nativeLanguage,
    native: activity.prompt_native ?? activity.instruction_native,
    legacyPortuguese: activity.prompt_pt,
  });
  const stimulus = (activity.prompt_target || activity.prompt || "").trim();
  return {
    nativeLanguage,
    gloss,
    instruction,
    stimulus: stimulus && stimulus !== instruction ? stimulus : "",
    visibility: activity.support_visibility ?? supportVisibility,
  };
}

export const choiceClass = (selected: boolean, locked: boolean) =>
  `min-h-11 rounded-xl border px-4 py-3 text-left text-sm font-semibold outline-none motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
    selected
      ? "border-primary bg-primary-soft text-primary"
      : "border-border bg-surface text-text-primary hover:border-primary/40"
  } ${locked ? "cursor-not-allowed opacity-80" : ""}`;
