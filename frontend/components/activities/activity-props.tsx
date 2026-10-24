"use client";

import type { TeachingActivity } from "@/types/teaching";
import { supportText } from "@/lib/bilingual";
import { useLearnerNativeLanguage } from "@/components/native-language-context";
import type { KeyboardEvent } from "react";

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

/** Move o foco entre botões irmãos. Enter e Espaço continuam ativando o botão. */
export function focusSiblingButton(event: KeyboardEvent<HTMLElement>) {
  if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
  const buttons = Array.from(
    event.currentTarget.querySelectorAll<HTMLButtonElement>("button:not(:disabled)"),
  );
  const current = buttons.indexOf(event.target as HTMLButtonElement);
  if (current < 0 || buttons.length === 0) return;
  event.preventDefault();
  const delta = event.key === "ArrowRight" ? 1 : -1;
  buttons[(current + delta + buttons.length) % buttons.length]?.focus();
}
