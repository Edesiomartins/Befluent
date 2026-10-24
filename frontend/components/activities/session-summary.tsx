import type { SessionAreaProgress } from "@/components/session-progress";
import { masteryLabel } from "@/lib/teaching-phase-label";

export function SessionSummary({
  total,
  completed,
  areas = [],
  masteryState,
  correct,
  masteredWords,
  minutes,
}: {
  total?: number | null;
  completed?: number | null;
  areas?: SessionAreaProgress[];
  masteryState?: string | null;
  correct?: number | null;
  masteredWords?: number | null;
  minutes?: number | null;
}) {
  const mastery = masteryLabel(masteryState);
  const remaining =
    total != null && completed != null ? Math.max(total - completed, 0) : null;
  const highlights = [
    typeof correct === "number" ? { label: "Acertos", value: correct } : null,
    typeof masteredWords === "number" ? { label: "Palavras dominadas", value: masteredWords } : null,
    typeof minutes === "number" ? { label: "Minutos", value: minutes } : null,
  ].filter((item): item is { label: string; value: number } => item !== null);

  return (
    <div role="status">
      <h2 className="text-xl font-semibold motion-safe:animate-[session-rise_480ms_ease-out] motion-reduce:animate-none">
        Sessão concluída
      </h2>
      <p className="mt-3 text-sm leading-6 text-text-secondary">
        Este bloco terminou. Os itens que precisam de reforço voltam depois.
      </p>
      {highlights.length > 0 && (
        <ul className="mx-auto mt-5 grid max-w-md grid-cols-[repeat(auto-fit,minmax(7rem,1fr))] gap-3 text-left">
          {highlights.map((item) => (
            <li key={item.label} className="rounded-xl bg-success/10 px-3 py-3">
              <p className="display-number text-2xl leading-none text-success">{item.value}</p>
              <p className="mt-1 text-xs text-text-secondary">{item.label}</p>
            </li>
          ))}
        </ul>
      )}
      {total ? (
        <p className="mt-2 text-sm text-text-secondary">{total} exercícios nesta sessão.</p>
      ) : null}
      {remaining != null && remaining > 0 && (
        <p className="mt-2 text-sm text-text-secondary">Faltam {remaining}.</p>
      )}
      {mastery && <p className="mt-2 text-sm font-semibold text-text-primary">Estado: {mastery}</p>}
      {areas.length > 0 && (
        <ul className="mx-auto mt-4 max-w-sm space-y-1 text-left text-sm text-text-secondary">
          {areas.map((area) => (
            <li key={area.key} className="flex justify-between gap-3">
              <span>{area.label}</span>
              <span className="tabular-nums">{area.total}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
