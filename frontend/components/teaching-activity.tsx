"use client";

import { useState } from "react";
import { ChoiceFeedbackPanel } from "@/components/objective-choice";
import { AudioPlayer, Recorder } from "@/components/study";
import type { AnswerFeedback, TeachingActivity } from "@/types/teaching";

export function TeachingActivityBody({
  activity,
  response,
  onResponse,
  locked = false,
  languageCode = "en",
}: {
  activity: TeachingActivity;
  response: string;
  onResponse: (value: string) => void;
  locked?: boolean;
  languageCode?: string;
}) {
  const [responseMode, setResponseMode] = useState<"typing" | "speech">("typing");

  if (activity.type === "presentation") {
    const termAudio = activity.audio_targets?.find(
      (target) => target.audio_target_type === "vocabulary_item",
    );
    const exampleAudio = activity.audio_targets?.find(
      (target) => target.audio_target_type === "example_sentence",
    );
    return (
      <div className="space-y-6">
        {activity.prompt_pt && (
          <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        )}
        <div>
          <p className="label">Expressão</p>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <h2 className="text-3xl font-semibold tracking-tight">{activity.term}</h2>
            {termAudio?.audio_text && (
              <AudioPlayer
                variant="compact"
                accessibleName={`Ouvir expressão ${activity.term ?? ""}`.trim()}
                text={termAudio.audio_text}
                languageCode={languageCode}
              />
            )}
          </div>
          {activity.reading_or_pinyin && (
            <p className="mt-2 text-sm text-text-secondary">{activity.reading_or_pinyin}</p>
          )}
          {activity.translation_pt && (
            <p className="mt-3 text-lg text-text-secondary">{activity.translation_pt}</p>
          )}
        </div>
        {activity.example_sentence && (
          <div className="border-t border-border pt-5">
            <p className="label">Frase de exemplo</p>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <p className="font-medium text-text-primary">{activity.example_sentence}</p>
              {exampleAudio?.audio_text && (
                <AudioPlayer
                  variant="compact"
                  accessibleName="Ouvir frase de exemplo"
                  text={exampleAudio.audio_text}
                  languageCode={languageCode}
                />
              )}
            </div>
            {activity.example_translation_pt && (
              <p className="mt-2 text-sm text-text-secondary">
                {activity.example_translation_pt}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  if (
    (activity.type === "recognition" && Boolean(activity.vocabulary_item_id)) ||
    activity.type === "reverse_recognition" ||
    activity.type === "listening_recognition"
  ) {
    const isListening = activity.type === "listening_recognition";
    const groupLabel =
      activity.prompt_pt ??
      (isListening ? "Opções da atividade de escuta" : "Opções da atividade");
    return (
      <div className="space-y-5">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        {!isListening && activity.show_text !== false && activity.prompt && (
          <p className="text-2xl font-semibold text-text-primary">{activity.prompt}</p>
        )}
        {isListening && activity.audio_text && (
          <AudioPlayer
            variant="compact"
            label="Ouvir"
            accessibleName={
              activity.audio_target_type === "example_sentence"
                ? "Ouvir frase de exemplo"
                : "Ouvir expressão"
            }
            text={activity.audio_text}
            languageCode={languageCode}
          />
        )}
        <div className="grid gap-2" role="radiogroup" aria-label={groupLabel}>
          {(activity.options ?? []).map((option) => {
            const selected = response === option;
            return (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={selected}
                disabled={locked}
                onClick={() => {
                  if (!locked) onResponse(option);
                }}
                className={`rounded-xl border px-4 py-3 text-left text-sm font-semibold outline-none transition focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
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

  if (activity.type === "lexical_production") {
    const allowsSpeech = activity.response_modes?.includes("speech") ?? false;
    return (
      <div className="space-y-5">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        {activity.prompt && (
          <p className="text-2xl font-semibold text-text-primary">{activity.prompt}</p>
        )}
        {allowsSpeech && (
          <div
            className="flex flex-wrap gap-2"
            role="radiogroup"
            aria-label="Modo de resposta"
          >
            {[
              { value: "typing" as const, label: "Digitar" },
              { value: "speech" as const, label: "Falar" },
            ].map((mode) => (
              <button
                key={mode.value}
                type="button"
                role="radio"
                aria-checked={responseMode === mode.value}
                disabled={locked}
                onClick={() => setResponseMode(mode.value)}
                className={`rounded-[10px] border px-4 py-2.5 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
                  responseMode === mode.value
                    ? "border-primary bg-primary-soft text-primary"
                    : "border-border bg-surface text-text-primary"
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        )}
        {responseMode === "speech" && allowsSpeech ? (
          <div>
            <Recorder onTranscript={onResponse} languageCode={languageCode} />
            {response && (
              <p className="mt-3 text-sm text-text-secondary" role="status">
                Transcrição: <span className="font-medium text-text-primary">{response}</span>
              </p>
            )}
          </div>
        ) : (
          <textarea
            aria-label="Sua resposta"
            value={response}
            disabled={locked}
            onChange={(event) => onResponse(event.target.value)}
            rows={3}
            className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none ring-primary focus:ring-2 disabled:opacity-70"
            placeholder="Digite o termo"
          />
        )}
      </div>
    );
  }

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
        <details className="disclosure rounded-lg border border-border px-4 py-3 text-sm">
          <summary className="cursor-pointer font-semibold text-primary">Ver ajuda</summary>
          <p className="mt-3 leading-6 text-text-secondary">{activity.scaffold_pt}</p>
        </details>
      )}
      {activity.type === "fill_gap" && (
        <p className="font-medium text-text-primary">{activity.prompt}</p>
      )}
      <textarea
        aria-label="Sua resposta"
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
