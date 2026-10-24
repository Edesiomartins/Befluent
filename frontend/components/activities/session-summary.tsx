import type { SessionAreaProgress } from "@/components/session-progress";
import { masteryLabel } from "@/lib/teaching-phase-label";

export function SessionSummary({
  total,
  completed,
  areas = [],
  masteryState,
}: {
  total?: number | null;
  completed?: number | null;
  areas?: SessionAreaProgress[];
  masteryState?: string | null;
}) {
  const mastery = masteryLabel(masteryState);
  const remaining =
    total != null && completed != null ? Math.max(total - completed, 0) : null;

  return (
    <div role="status">
      <h2 className="text-xl font-semibold">Sessão concluída</h2>
      <p className="mt-3 text-sm leading-6 text-text-secondary">
        Este bloco terminou. Os itens que precisam de reforço voltam depois.
      </p>
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
