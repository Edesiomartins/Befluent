"use client";

import { useEffect, useId, useRef } from "react";
import type { AnswerFeedback } from "@/types/teaching";

export function FeedbackSheet({
  feedback,
  canRetry,
  onContinue,
  onRetry,
}: {
  feedback: AnswerFeedback;
  canRetry: boolean;
  onContinue: () => void;
  onRetry: () => void;
}) {
  const titleId = useId();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const correct = feedback.is_correct;
  const explanation = feedback.why_correct || feedback.why_selected || feedback.remember || "";

  useEffect(() => {
    titleRef.current?.focus();
  }, [feedback]);

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 bg-surface/95 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-md">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={`mx-auto w-full max-w-2xl rounded-2xl border p-5 shadow-2xl ${
          correct ? "border-success bg-success/10" : "border-danger bg-danger/10"
        }`}
      >
        <h2
          ref={titleRef}
          id={titleId}
          tabIndex={-1}
          className={`text-lg font-semibold outline-none ${correct ? "text-success" : "text-danger"}`}
        >
          {correct ? "Correto." : "Resposta incorreta"}
        </h2>
        <div aria-live="assertive" className="mt-2 text-sm leading-6 text-text-primary">
          <p>{correct ? "Correto." : "Resposta incorreta"}</p>
          {!correct && (
            <p className="mt-2">
              <span className="font-semibold">Resposta correta:</span> {feedback.correct_option}
            </p>
          )}
          {explanation && <p className="mt-2">{explanation}</p>}
          {canRetry && !correct && (
            <p className="mt-2 text-text-secondary">
              Tentar novamente mantém esta atividade, este objetivo e o idioma que você está estudando.
            </p>
          )}
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            className="min-h-12 rounded-xl bg-primary text-sm font-semibold text-white shadow-[0_1px_2px_rgba(15,23,42,0.12)] hover:bg-[var(--primary-hover)]"
            onClick={onContinue}
          >
            Continuar
          </button>
          {canRetry && (
            <button
              type="button"
              className="min-h-12 rounded-xl border border-border bg-surface text-sm font-semibold text-text-primary hover:bg-[var(--surface-soft)]"
              onClick={onRetry}
            >
              Tentar novamente
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
