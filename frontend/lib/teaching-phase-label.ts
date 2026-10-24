const LABELS: Record<string, string> = {
  not_started: "Início",
  activating: "Aquecimento",
  input: "Descoberta",
  noticing: "Observe",
  practicing: "Prática",
  producing: "Produção",
  evaluating: "Avaliação",
  needs_remediation: "Revisão",
  retrying: "Nova tentativa",
  transfer_check: "Desafio",
  mastered: "Concluído",
  needs_review: "Revisão",
};

/** Rótulo pedagógico da fase. O enum interno não aparece para o aluno. */
export function teachingPhaseLabel(phase?: string | null, fallback?: string | null): string {
  if (phase && LABELS[phase]) return LABELS[phase];
  const text = fallback?.trim();
  return text || "Prática";
}

const MASTERY: Record<string, string> = {
  mastered: "Dominado",
  needs_review: "Precisa de revisão",
  practicing: "Em prática",
  learning: "Em prática",
};

/** Só traduz estados que o backend realmente enviou. */
export function masteryLabel(state?: string | null): string | null {
  if (!state) return null;
  return MASTERY[state] ?? null;
}
