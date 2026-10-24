"use client";

import { useEffect, useRef } from "react";
import { ChoiceFeedbackPanel } from "@/components/objective-choice";
import type { AnswerFeedback } from "@/types/teaching";

export function ActivityFeedback({
  feedback,
  sameObjectiveRetry = true,
  showRetryNote = true,
}: {
  feedback: AnswerFeedback | null | undefined;
  sameObjectiveRetry?: boolean;
  showRetryNote?: boolean;
}) {
  const region = useRef<HTMLDivElement>(null);
  useEffect(() => {
    region.current?.focus();
  }, [feedback]);

  if (!feedback) return null;
  return (
    <div
      ref={region}
      tabIndex={-1}
      aria-live="polite"
      className="outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <ChoiceFeedbackPanel feedback={feedback} />
      {showRetryNote && !feedback.is_correct && (
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          {sameObjectiveRetry
            ? "Tentar novamente mantém esta atividade, este objetivo e o idioma que você está estudando."
            : "Esta tentativa usa outra interação do mesmo objetivo, no mesmo idioma."}
        </p>
      )}
    </div>
  );
}
