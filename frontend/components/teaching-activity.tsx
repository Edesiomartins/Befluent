"use client";

import { ChoiceFeedbackPanel } from "@/components/objective-choice";
import type { AnswerFeedback, TeachingActivity } from "@/types/teaching";

export function TeachingActivityBody({
  activity,
  response,
  onResponse,
  locked = false,
}: {
  activity: TeachingActivity;
  response: string;
  onResponse: (value: string) => void;
  locked?: boolean;
}) {
  if (activity.type === "listen" || activity.type === "recognition") {
    const lines = activity.models ?? activity.examples ?? [];
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        {activity.title_pt && (
          <p className="text-lg font-semibold text-text-primary">{activity.title_pt}</p>
        )}
        {activity.can_do && (
          <p className="rounded-xl bg-surface-elevated px-4 py-3 text-sm leading-6 text-text-primary">
            {activity.can_do}
          </p>
        )}
        {lines.length > 0 && (
          <ul className="space-y-2">
            {lines.map((line) => (
              <li
                key={line}
                className="rounded-xl border border-border bg-surface px-4 py-3 font-medium text-text-primary"
              >
                {line}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (activity.type === "multiple_choice") {
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        <p className="font-medium text-text-primary">{activity.prompt}</p>
        {activity.is_retry_variant && (
          <p className="text-xs text-text-secondary">
            Nova tentativa com contexto diferente — a questão anterior permanece fechada.
          </p>
        )}
        <div className="grid gap-2" role="radiogroup">
          {(activity.options ?? []).map((option) => {
            const selected = response === option;
            return (
              <button
                key={option}
                type="button"
                disabled={locked}
                onClick={() => {
                  if (!locked) onResponse(option);
                }}
                className={`rounded-xl border px-4 py-3 text-left text-sm font-semibold transition ${
                  selected
                    ? "border-primary bg-primary-soft text-primary"
                    : "border-border bg-surface text-text-primary hover:border-primary/40"
                } ${locked ? "cursor-not-allowed opacity-80" : ""}`}
              >
                {option}
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  if (activity.type === "word_order") {
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        <p className="text-sm text-text-secondary">
          Palavras: {(activity.tokens ?? []).join(" · ")}
        </p>
        <textarea
          value={response}
          disabled={locked}
          onChange={(event) => onResponse(event.target.value)}
          rows={3}
          className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none ring-primary focus:ring-2 disabled:opacity-70"
          placeholder="Escreva a frase na ordem correta"
        />
      </div>
    );
  }

  if (activity.type === "matching") {
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        <ul className="space-y-2">
          {(activity.pairs ?? []).map((pair) => (
            <li key={pair.term} className="rounded-xl border border-border px-4 py-3">
              <span className="font-semibold text-text-primary">{pair.term}</span>
              <span className="mt-1 block text-sm text-text-secondary">{pair.hint_pt}</span>
            </li>
          ))}
        </ul>
        <p className="text-sm text-text-secondary">
          Leia os pares e continue quando estiver pronto.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
      {activity.prompt && (
        <p className="text-lg font-semibold text-text-primary">{activity.prompt}</p>
      )}
      {activity.scaffold_pt && (
        <p className="rounded-xl bg-surface-elevated px-4 py-3 text-sm text-text-secondary">
          Apoio: {activity.scaffold_pt}
        </p>
      )}
      {activity.type === "fill_gap" && (
        <p className="font-medium text-text-primary">{activity.prompt}</p>
      )}
      <textarea
        value={response}
        disabled={locked}
        onChange={(event) => onResponse(event.target.value)}
        rows={4}
        className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none ring-primary focus:ring-2 disabled:opacity-70"
        placeholder="Sua resposta"
      />
    </div>
  );
}

export function TeachingAnswerFeedback({
  feedback,
}: {
  feedback: AnswerFeedback | null | undefined;
}) {
  if (!feedback) return null;
  return <ChoiceFeedbackPanel feedback={feedback} />;
}
