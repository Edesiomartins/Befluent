"use client";

import { useState } from "react";
import { Recorder } from "@/components/study";
import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";
import { TargetLine } from "@/components/bilingual-text";

const fieldClass =
  "w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70";

export function RecallActivity({
  activity,
  response,
  onResponse,
  locked = false,
  languageCode = "",
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction, stimulus } = useActivityCopy(activity, supportVisibility);
  const [responseMode, setResponseMode] = useState<"typing" | "speech">("typing");
  const allowsSpeech = activity.response_modes?.includes("speech") ?? false;

  return (
    <div className="space-y-5">
      <p className="label">Recuperar</p>
      {instruction && <p className="border-b border-border pb-3 text-sm leading-6 text-text-secondary">{instruction}</p>}
      {stimulus && <TargetLine text={stimulus} />}
      <p className="text-sm text-text-secondary">
        A tarefa é recuperar a forma no idioma estudado, não apenas reconhecê-la.
      </p>
      {allowsSpeech && (
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Modo de resposta">
          {(
            [
              { value: "typing" as const, label: "Digitar" },
              { value: "speech" as const, label: "Falar" },
            ]
          ).map((mode) => (
            <button
              key={mode.value}
              type="button"
              role="radio"
              aria-checked={responseMode === mode.value}
              disabled={locked}
              onClick={() => setResponseMode(mode.value)}
              className={`min-h-11 rounded-[10px] border px-4 py-2.5 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
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
          className={fieldClass}
          placeholder="Digite o termo"
        />
      )}
    </div>
  );
}
