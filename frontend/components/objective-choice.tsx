"use client";

/**
 * Questão objetiva com tentativa única autoritativa no backend.
 *
 * Antes do envio: troca de seleção livre.
 * Depois: opções bloqueadas + feedback pedagógico do servidor.
 * sessionStorage NÃO é autoridade — só cache opcional de UX.
 */

import { useEffect, useId, useMemo, useState } from "react";
import { Button } from "@/components/ui";
import { ApiError, api } from "@/lib/api";

export type ObjectiveChoiceQuestion = {
  prompt: string;
  options: string[];
  /** Gabarito só para fallback offline/testes sem lessonId — backend ignora. */
  answer?: string;
  rationale?: string;
  option_rationales?: Record<string, string>;
  remember?: string;
  is_retry_variant?: boolean;
};

export type ChoiceFeedback = {
  is_correct: boolean;
  selected: string;
  correct_option: string;
  why_selected?: string | null;
  why_correct?: string | null;
  remember?: string | null;
};

export type RetryOffer = {
  available: boolean;
  strategy?: string;
  message?: string;
  activity?: {
    prompt?: string;
    options?: string[];
    rationale?: string;
    option_rationales?: Record<string, string>;
    is_retry_variant?: boolean;
  } | null;
};

type AttemptPayload = {
  attempt_id: string;
  activity_key: string;
  attempt_number: number;
  submitted: boolean;
  correct: boolean;
  selected_answer?: string | null;
  correct_answer?: string | null;
  feedback?: ChoiceFeedback;
  revealed_correct_answer?: boolean;
  retry?: RetryOffer;
  pedagogical_effect?: string;
  question_snapshot?: {
    prompt?: string;
    options?: string[];
  };
};

function activityKeyFor(surface: string, kind: string, index: number) {
  return `${surface}:${kind}:${index}`;
}

function clientFallbackFeedback(
  question: ObjectiveChoiceQuestion,
  selected: string,
): ChoiceFeedback {
  const answer = question.answer ?? "";
  const isCorrect = Boolean(answer) && selected === answer;
  const whyCorrect =
    question.rationale?.trim() ||
    (answer
      ? `A resposta adequada é «${answer}», conforme a regra desta atividade.`
      : "Consulte a explicação da atividade.");
  if (isCorrect) {
    return {
      is_correct: true,
      selected,
      correct_option: answer,
      why_correct: whyCorrect,
      remember: question.remember ?? null,
    };
  }
  const distractor = question.option_rationales?.[selected]?.trim();
  return {
    is_correct: false,
    selected,
    correct_option: answer,
    why_selected:
      distractor ||
      `Esta opção não aplica a regra desta atividade. ${whyCorrect}`.trim(),
    why_correct: whyCorrect,
    remember: question.remember ?? null,
  };
}

export function ChoiceFeedbackPanel({ feedback }: { feedback: ChoiceFeedback }) {
  if (feedback.is_correct) {
    return (
      <div
        role="status"
        tabIndex={-1}
        className="mt-4 rounded-lg border border-success/30 bg-success/10 p-4 text-sm leading-6 text-success"
      >
        <p className="font-semibold">Correto.</p>
        <p className="mt-2 text-text-primary">
          <span className="font-semibold">Você respondeu:</span> {feedback.selected}
        </p>
        {feedback.why_correct && (
          <p className="mt-2 text-text-primary">{feedback.why_correct}</p>
        )}
        {feedback.remember && (
          <p className="mt-2 text-text-secondary">Lembre-se: {feedback.remember}</p>
        )}
      </div>
    );
  }
  return (
    <div
      role="status"
      tabIndex={-1}
      className="mt-4 rounded-lg border border-danger/30 bg-danger/10 p-4 text-sm leading-6"
    >
      <p className="font-semibold text-danger">Resposta incorreta</p>
      <p className="mt-3 text-text-primary">
        <span className="font-semibold">Você respondeu:</span> {feedback.selected}
      </p>
      {feedback.why_selected && (
        <p className="mt-2 text-text-secondary">
          <span className="font-semibold text-text-primary">Por que não funciona aqui:</span>{" "}
          {feedback.why_selected}
        </p>
      )}
      <p className="mt-3 text-text-primary">
        <span className="font-semibold">Resposta correta:</span> {feedback.correct_option}
      </p>
      {feedback.why_correct && (
        <p className="mt-2 text-text-secondary">
          <span className="font-semibold text-text-primary">Por que funciona:</span>{" "}
          {feedback.why_correct}
        </p>
      )}
      {feedback.remember && (
        <p className="mt-3 text-text-secondary">Lembre-se: {feedback.remember}</p>
      )}
    </div>
  );
}

function normalizeFeedback(raw: AttemptPayload): ChoiceFeedback | null {
  const fb = raw.feedback;
  if (fb && typeof fb.is_correct === "boolean") {
    return {
      is_correct: fb.is_correct,
      selected: fb.selected || String(raw.selected_answer || ""),
      correct_option: fb.correct_option || String(raw.correct_answer || ""),
      why_selected: fb.why_selected,
      why_correct: fb.why_correct,
      remember: fb.remember,
    };
  }
  if (raw.selected_answer) {
    return {
      is_correct: Boolean(raw.correct),
      selected: String(raw.selected_answer),
      correct_option: String(raw.correct_answer || ""),
    };
  }
  return null;
}

export function ObjectiveChoice({
  question,
  index = 0,
  lessonId,
  activityKey,
  surface = "lesson",
  kind = "question",
  onEvaluated,
}: {
  question: ObjectiveChoiceQuestion;
  index?: number;
  lessonId?: string;
  /** Identidade estável; default surface:kind:index */
  activityKey?: string;
  surface?: string;
  kind?: string;
  onEvaluated?: (feedback: ChoiceFeedback) => void;
}) {
  const resolvedKey = useMemo(
    () => activityKey ?? activityKeyFor(surface, kind, index),
    [activityKey, surface, kind, index],
  );
  const groupId = useId();
  const [displayQuestion, setDisplayQuestion] = useState(question);
  const [selected, setSelected] = useState("");
  const [locked, setLocked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<ChoiceFeedback | null>(null);
  const [retry, setRetry] = useState<RetryOffer | null>(null);
  const [isRetrySubmit, setIsRetrySubmit] = useState(false);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [correctOption, setCorrectOption] = useState(question.answer ?? "");

  useEffect(() => {
    setDisplayQuestion(question);
    setCorrectOption(question.answer ?? "");
  }, [question]);

  useEffect(() => {
    if (!lessonId) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api<{ attempts: AttemptPayload[] }>(
          `/api/v1/lessons/${lessonId}/objective-attempts`,
        );
        if (cancelled) return;
        const mine = (data.attempts || [])
          .filter((a) => a.activity_key === resolvedKey && a.submitted)
          .sort((a, b) => b.attempt_number - a.attempt_number);
        const latest = mine[0];
        if (!latest) return;
        const nextFeedback = normalizeFeedback(latest);
        setSelected(String(latest.selected_answer || ""));
        setLocked(true);
        setFeedback(nextFeedback);
        setCorrectOption(String(latest.correct_answer || nextFeedback?.correct_option || ""));
        setRetry(latest.retry ?? null);
        if (latest.question_snapshot?.prompt && latest.question_snapshot.options) {
          setDisplayQuestion((prev) => ({
            ...prev,
            prompt: latest.question_snapshot!.prompt || prev.prompt,
            options: latest.question_snapshot!.options || prev.options,
          }));
        }
      } catch {
        if (!cancelled) {
          setRestoreError("Não foi possível restaurar a tentativa. Tente recarregar.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lessonId, resolvedKey]);

  async function submit() {
    if (!selected || locked || submitting) return;
    setSubmitting(true);
    setRestoreError(null);

    if (!lessonId) {
      // Sem lessonId: só testes/local — não é superfície de produção.
      const next = clientFallbackFeedback(displayQuestion, selected);
      setFeedback(next);
      setCorrectOption(next.correct_option);
      setLocked(true);
      onEvaluated?.(next);
      setSubmitting(false);
      return;
    }

    try {
      const result = await api<AttemptPayload>(
        `/api/v1/lessons/${lessonId}/objective-answers`,
        {
          method: "POST",
          body: {
            activity_key: resolvedKey,
            selected_answer: selected,
            request_retry: isRetrySubmit,
          },
        },
      );
      const next = normalizeFeedback(result);
      if (!next) throw new Error("Resposta sem feedback");
      setFeedback(next);
      setCorrectOption(String(result.correct_answer || next.correct_option));
      setLocked(true);
      setRetry(result.retry ?? null);
      setIsRetrySubmit(false);
      onEvaluated?.(next);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        // Backend já tem tentativa — restaurar, nunca “desbloquear”.
        try {
          const data = await api<{ attempts: AttemptPayload[] }>(
            `/api/v1/lessons/${lessonId}/objective-attempts`,
          );
          const latest = (data.attempts || [])
            .filter((a) => a.activity_key === resolvedKey && a.submitted)
            .sort((a, b) => b.attempt_number - a.attempt_number)[0];
          if (latest) {
            const next = normalizeFeedback(latest);
            setSelected(String(latest.selected_answer || selected));
            setLocked(true);
            setFeedback(next);
            setCorrectOption(
              String(latest.correct_answer || next?.correct_option || ""),
            );
            setRetry(latest.retry ?? null);
            if (next) onEvaluated?.(next);
          }
        } catch {
          setRestoreError("Esta tentativa já foi enviada. Recarregue a página.");
          setLocked(true);
        }
      } else {
        setRestoreError(
          err instanceof Error ? err.message : "Falha ao enviar a resposta.",
        );
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function startRetry() {
    if (!lessonId || !retry?.available || !retry.activity?.options?.length) return;
    setDisplayQuestion({
      prompt: retry.activity.prompt || displayQuestion.prompt,
      options: retry.activity.options,
      rationale: retry.activity.rationale,
      option_rationales: retry.activity.option_rationales,
    });
    setSelected("");
    setFeedback(null);
    setLocked(false);
    setIsRetrySubmit(true);
    setRetry(null);
    setCorrectOption("");
  }

  const showContinueFallback =
    locked && feedback && !feedback.is_correct && retry && !retry.available;

  return (
    <div>
      <p className="text-sm text-text-secondary">Escolha uma alternativa e confirme.</p>
      {displayQuestion.is_retry_variant || isRetrySubmit ? (
        <p className="mt-2 text-xs text-text-secondary">
          Nova tentativa — a resposta anterior permanece registrada e fechada.
        </p>
      ) : null}
      <p className="mt-3 text-xl font-medium">{displayQuestion.prompt}</p>
      <div className="mt-5 grid gap-2" role="radiogroup" aria-label={displayQuestion.prompt}>
        {displayQuestion.options.map((option) => {
          const isSelected = selected === option;
          const isCorrectOption = locked && correctOption && option === correctOption;
          const isWrongSelected =
            locked && isSelected && correctOption && option !== correctOption;
          return (
            <label
              key={option}
              className={`rounded-lg border p-3 transition ${
                isCorrectOption
                  ? "border-success bg-success/10"
                  : isWrongSelected
                    ? "border-danger bg-danger/10"
                    : isSelected
                      ? "border-primary bg-primary/5"
                      : "border-border"
              } ${locked ? "cursor-not-allowed opacity-95" : "cursor-pointer"}`}
            >
              <input
                className="mr-3 accent-[var(--primary)]"
                type="radio"
                name={`${groupId}-${resolvedKey}`}
                checked={isSelected}
                disabled={locked || submitting}
                onChange={() => {
                  if (!locked) setSelected(option);
                }}
              />
              <span>
                {option}
                {locked && isCorrectOption ? (
                  <span className="ml-2 text-xs font-semibold text-success">
                    (resposta correta)
                  </span>
                ) : null}
                {locked && isWrongSelected ? (
                  <span className="ml-2 text-xs font-semibold text-danger">
                    (você respondeu)
                  </span>
                ) : null}
              </span>
            </label>
          );
        })}
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          disabled={!selected || locked || submitting}
          loading={submitting}
          onClick={() => void submit()}
        >
          {locked ? "Resposta enviada" : "Enviar resposta"}
        </Button>
        {locked && retry?.available && retry.activity?.options?.length ? (
          <Button variant="secondary" onClick={() => void startRetry()}>
            Nova tentativa
          </Button>
        ) : null}
      </div>
      {showContinueFallback && (
        <p className="mt-3 text-sm text-text-secondary" role="status">
          {retry?.message ||
            "Não há variante segura agora. Continue o percurso; o erro fica para revisão."}
        </p>
      )}
      {restoreError && (
        <p className="mt-3 text-sm text-danger" role="alert">
          {restoreError}
        </p>
      )}
      {feedback && <ChoiceFeedbackPanel feedback={feedback} />}
    </div>
  );
}
