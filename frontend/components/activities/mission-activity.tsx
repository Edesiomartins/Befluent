"use client";

import { useActivityCopy, type ActivityRenderProps } from "@/components/activities/activity-props";

export function DialogueActivity({ activity, supportVisibility }: ActivityRenderProps) {
  const { gloss, instruction, stimulus } = useActivityCopy(activity, supportVisibility);
  const scene = (activity.scenario_target || stimulus || "").trim();
  const sceneNative = gloss(activity.scenario_native, null);
  const help = gloss(activity.scaffold_native, activity.scaffold_pt);

  return (
    <div className="space-y-4">
      <p className="label">Missão</p>
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {scene && (
        <p className="font-medium text-text-primary">Você está nesta situação: {scene}</p>
      )}
      {sceneNative && sceneNative !== scene && (
        <p className="text-sm text-text-secondary">{sceneNative}</p>
      )}
      {activity.can_do && (
        <p className="text-sm text-text-primary">Seu objetivo é {activity.can_do}</p>
      )}
      <ol className="space-y-2 text-sm text-text-secondary" aria-label="Progresso da conversa">
        <li>1. O tutor fala no idioma estudado.</li>
        <li>2. Você responde no mesmo idioma.</li>
      </ol>
      {help && (
        <details className="disclosure rounded-lg border border-border px-4 py-3 text-sm">
          <summary className="cursor-pointer font-semibold text-primary">
            Expressões que podem ajudar
          </summary>
          <p className="mt-3 leading-6 text-text-secondary">{help}</p>
        </details>
      )}
      <p className="text-sm text-text-secondary">Leia a situação e continue quando estiver pronto.</p>
    </div>
  );
}

export function TransferActivity({
  activity,
  response,
  onResponse,
  locked = false,
  supportVisibility,
}: ActivityRenderProps) {
  const { instruction, stimulus } = useActivityCopy(activity, supportVisibility);

  return (
    <div className="space-y-4">
      <p className="label">Desafio</p>
      <p className="text-sm text-text-secondary">
        Use o que você praticou em um contexto diferente. O idioma continua o mesmo.
      </p>
      {instruction && <p className="leading-7 text-text-secondary">{instruction}</p>}
      {stimulus && <p className="text-lg font-semibold text-text-primary">{stimulus}</p>}
      <textarea
        aria-label="Sua resposta"
        value={response}
        disabled={locked}
        onChange={(event) => onResponse(event.target.value)}
        rows={4}
        className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70"
        placeholder="Sua resposta"
      />
    </div>
  );
}

export function UnsupportedActivity() {
  return (
    <p role="status" className="text-sm leading-6 text-text-secondary">
      Esta atividade não tem uma interação definida. Ela não abre como texto livre.
    </p>
  );
}
