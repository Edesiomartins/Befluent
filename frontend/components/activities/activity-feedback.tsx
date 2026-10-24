"use client";

import { ChoiceFeedbackPanel } from "@/components/objective-choice";
import type { AnswerFeedback } from "@/types/teaching";

export function ActivityFeedback({
  feedback,
  sameObjectiveRetry = true,
}: {
  feedback: AnswerFeedback | null | undefined;
  sameObjectiveRetry?: boolean;
}) {
  if (!feedback) return null;
  return (
    <div aria-live="polite">
      <ChoiceFeedbackPanel feedback={feedback} />
      {!feedback.is_correct && (
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          {sameObjectiveRetry
            ? "Tentar novamente mantém esta atividade, este objetivo e o idioma que você está estudando."
            : "Esta tentativa usa outra interação do mesmo objetivo, no mesmo idioma."}
        </p>
      )}
    </div>
  );
}
