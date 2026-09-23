export type LanguageAccessState = "available" | "entitled" | "locked";

const LABELS: Record<LanguageAccessState, string> = {
  available: "Disponível",
  entitled: "Liberado",
  locked: "Bloqueado",
};

const CLASS_NAMES: Record<LanguageAccessState, string> = {
  available: "bg-primary-soft text-primary",
  entitled: "bg-success/10 text-success",
  locked: "bg-warning/10 text-warning",
};

export function languageAccessLabel(state: LanguageAccessState): string {
  return LABELS[state];
}

export function LanguageAccessBadge({ state }: { state: LanguageAccessState }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${CLASS_NAMES[state]}`}
    >
      {languageAccessLabel(state)}
    </span>
  );
}
