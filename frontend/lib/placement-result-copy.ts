import { SKILL_LABELS, levelShortCode, type Skill } from "@/lib/levels";
import type {
  AssessmentCoverage,
  AssessmentCoverageSkill,
  PlacementResult,
  SkillResult,
} from "@/types/placement";

export const SKILL_ORDER: Skill[] = [
  "vocabulary_grammar",
  "reading",
  "listening",
  "writing",
  "speaking",
];

const STATUS_LABELS: Record<SkillResult["status"], string> = {
  assessed: "",
  estimated: "",
  provisional: "estimativa provisória",
  insufficient_evidence: "Faixa ainda não determinada",
  not_collected: "Ainda não avaliada",
  unavailable: "Avaliação não disponível",
  calibrating: "em calibração",
  not_assessed: "não avaliada",
  not_available: "não avaliada",
};

const PROGRESS_STATE_LABELS: Record<string, string> = {
  collecting: "em coleta",
  in_collection: "em coleta",
  confirmation_pending: "confirmação pendente",
  pending_confirmation: "confirmação pendente",
  completed: "concluída",
  estimated: "concluída",
  assessed: "concluída",
  provisional: "provisória",
};

export type SkillBandTone =
  | "estimated"
  | "provisional"
  | "pending"
  | "insufficient"
  | "unavailable"
  | "not_collected"
  | "other";

export const PARTIAL_PROFILE_TITLE = "Perfil de competências";

export const PARTIAL_PROFILE_LEAD =
  "Ainda não há evidência suficiente para determinar um nível global com segurança.";

/** Cobertura obrigatória cumprida (cinco competências), mas sem global suficiente. */
export const COVERED_PARTIAL_PROFILE_LEAD =
  "As cinco competências foram avaliadas, mas ainda não há evidência suficiente para determinar um nível global com segurança.";

export const INCOMPLETE_ASSESSMENT_TITLE = "Avaliação incompleta";

export const INCOMPLETE_ASSESSMENT_LEAD =
  "Nem todas as competências puderam ser avaliadas nesta sessão. Seu perfil abaixo mostra apenas as evidências realmente coletadas.";

export const PLANNING_LEVEL_NOTE =
  "Esse nível é usado apenas para iniciar seu plano de estudo e será ajustado conforme novas evidências forem coletadas.";

export function isPartialProfile(result: PlacementResult): boolean {
  if (result.profile_status === "complete" || result.overall_estimate_status === "sufficient") {
    return false;
  }
  return result.profile_status === "partial" || result.overall_estimate_status === "partial";
}

export function hasMeasuredOverall(result: PlacementResult): boolean {
  return Boolean(result.overall_level) && !isPartialProfile(result);
}

export type ResultMode = "measured" | "incomplete" | "covered_partial" | "partial" | "calibrating" | "other";

/** Decide a tela a partir do backend; nenhuma suficiência é recalculada aqui. */
export function resultMode(result: PlacementResult): ResultMode {
  if (hasMeasuredOverall(result)) return "measured";
  const partial = isPartialProfile(result);
  if (result.assessment_status === "incomplete") return "incomplete";
  if (partial && (result.assessment_status === "complete" || result.assessment_coverage?.mandatory_complete)) {
    return "covered_partial";
  }
  if (partial) return "partial";
  if (result.diagnostic_status === "calibrating") return "calibrating";
  return "other";
}

export function partialLead(mode: ResultMode): string {
  if (mode === "incomplete") return INCOMPLETE_ASSESSMENT_LEAD;
  if (mode === "covered_partial") return COVERED_PARTIAL_PROFILE_LEAD;
  return PARTIAL_PROFILE_LEAD;
}

const COVERAGE_REASON_NOTES: Record<string, string> = {
  user_skipped: "Esta atividade foi pulada.",
  microphone_unavailable: "Não foi possível acessar o microfone nesta sessão.",
  production_unavailable: "Não foi possível realizar esta atividade nesta sessão.",
  hard_technical_failure: "Uma falha técnica impediu esta atividade nesta sessão.",
  bank_exhausted: "Não há mais atividades adequadas disponíveis para completar esta competência nesta sessão.",
  bank_freshness_exhausted: "Não há mais atividades inéditas adequadas para completar esta competência nesta sessão.",
  maximum_reached: "A sessão atingiu o limite de atividades antes de completar esta competência.",
};

const SKIP_REASONS = new Set([
  "user_skipped", "microphone_unavailable", "production_unavailable", "hard_technical_failure",
]);

/** Motivo devolvido pelo backend em linguagem simples; código desconhecido não vira texto. */
export function coverageReasonNote(reason: string | null | undefined): string | null {
  if (!reason) return null;
  return COVERAGE_REASON_NOTES[reason] ?? null;
}

/** Motivo da skill: cobertura primeiro, depois as razões da própria skill. */
export function skillCoverageReason(
  skill: SkillResult,
  coverage: AssessmentCoverage | null | undefined,
): string | null {
  const entry = coverage?.skills?.[skill.skill];
  if (entry && !entry.satisfied && entry.reason) return entry.reason;
  const own = skill.skill_confidence?.reasons?.find((reason) => reason in COVERAGE_REASON_NOTES);
  return own ?? null;
}

export function skillWasSkipped(
  skill: SkillResult,
  coverage: AssessmentCoverage | null | undefined,
): boolean {
  if (skill.status !== "not_collected") return false;
  const entry = coverage?.skills?.[skill.skill];
  if (entry?.skipped) return true;
  const reason = skillCoverageReason(skill, coverage);
  return reason != null && SKIP_REASONS.has(reason);
}

/** Garante as cinco competências quando o backend descreve a cobertura delas. */
export function withAllSkills(
  skills: SkillResult[],
  coverage: AssessmentCoverage | null | undefined,
): SkillResult[] {
  if (!coverage?.skills) return skills;
  const present = new Set(skills.map((skill) => skill.skill));
  const missing = SKILL_ORDER.filter((skill) => skill in (coverage.skills ?? {}) && !present.has(skill));
  return [
    ...skills,
    ...missing.map<SkillResult>((skill) => ({
      skill,
      label: SKILL_LABELS[skill],
      estimated_level: null,
      level: null,
      score: null,
      max_score: null,
      status: "not_collected",
    })),
  ];
}

export function orderedSkills(skills: SkillResult[]): SkillResult[] {
  return [...skills].sort((left, right) => {
    const leftIndex = SKILL_ORDER.indexOf(left.skill);
    const rightIndex = SKILL_ORDER.indexOf(right.skill);
    return (leftIndex === -1 ? 99 : leftIndex) - (rightIndex === -1 ? 99 : rightIndex);
  });
}

function levelCode(level: string): string {
  return levelShortCode(level) ?? level;
}

export function skillBandTone(skill: SkillResult): SkillBandTone {
  if ((skill.status === "estimated" || skill.status === "assessed") && skill.estimated_level) return "estimated";
  if (skill.status === "provisional" && skill.estimated_level) return "provisional";
  if (skill.status === "insufficient_evidence" && skill.candidate_level) return "pending";
  if (skill.status === "insufficient_evidence") return "insufficient";
  if (skill.status === "unavailable") return "unavailable";
  if (skill.status === "not_collected") return "not_collected";
  return "other";
}

export function skillBandLabel(skill: SkillResult, skipped = false): string {
  if (skipped && skill.status === "not_collected") return "Não avaliada";
  if ((skill.status === "estimated" || skill.status === "assessed") && skill.estimated_level) {
    return levelCode(skill.estimated_level);
  }
  if (skill.status === "provisional" && skill.estimated_level) {
    return `${levelCode(skill.estimated_level)} — provisório`;
  }
  if (skill.status === "insufficient_evidence" && skill.candidate_level) {
    return `${levelCode(skill.candidate_level)} — confirmação pendente`;
  }
  if (skill.status === "insufficient_evidence") return "Faixa ainda não determinada";
  if (skill.status === "unavailable") return "Avaliação não disponível";
  if (skill.status === "not_collected") return "Ainda não avaliada";
  return STATUS_LABELS[skill.status] || "Faixa ainda não determinada";
}

/** Saldo vem só de confirmation_remaining. confirmation_needed é TOTAL e não é subtraído aqui. */
function confirmationRemaining(skill: SkillResult): number | null {
  const remaining = skill.confirmation_remaining;
  return typeof remaining === "number" && Number.isFinite(remaining) ? Math.max(remaining, 0) : null;
}

export function skillConfirmationNote(skill: SkillResult): string | null {
  if (skill.status !== "insufficient_evidence" || !skill.candidate_level) return null;
  const level = levelCode(skill.candidate_level);
  const remaining = confirmationRemaining(skill);
  if (remaining === 1) {
    return `Falta mais 1 atividade ${level} independente para confirmar esta faixa.`;
  }
  if (remaining != null && remaining > 1) {
    return `Faltam mais ${remaining} atividades ${level} independentes para confirmar esta faixa.`;
  }
  const reason = skill.candidate_reason?.trim();
  if (reason && !/^[a-z0-9_]+$/.test(reason)) return reason;
  return `Esta faixa ainda precisa de confirmação com atividades ${level} independentes.`;
}

export function skillProgressLabel(info: {
  status?: string | null;
  candidate_level?: string | null;
} | null | undefined): string | null {
  const status = info?.status;
  if (!status) return null;
  if (status === "insufficient_evidence") {
    return info?.candidate_level ? "confirmação pendente" : null;
  }
  return PROGRESS_STATE_LABELS[status] ?? null;
}

function countLabel(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

const PRODUCTION_SKILLS = new Set<Skill>(["writing", "speaking"]);

/** Cobertura da coleta por competência durante o teste. Não é porcentagem de domínio. */
export function coverageProgressLabel(skill: Skill, entry: AssessmentCoverageSkill | undefined): string | null {
  if (!entry) return null;
  if (PRODUCTION_SKILLS.has(skill) || entry.required <= 1) {
    if (entry.satisfied) return "Concluída";
    if (entry.skipped) return "Pulada";
    return "Pendente";
  }
  return `${Math.min(entry.completed, entry.required)} de ${entry.required} atividades coletadas`;
}

export function coverageSkillsInOrder(
  coverage: AssessmentCoverage | null | undefined,
): { skill: Skill; entry: AssessmentCoverageSkill }[] {
  const skills = coverage?.skills;
  if (!skills) return [];
  return SKILL_ORDER.flatMap((skill) => {
    const entry = skills[skill];
    return entry ? [{ skill, entry }] : [];
  });
}

function listSkills(skills: Skill[]): string {
  const labels = skills.map((skill) => SKILL_LABELS[skill]);
  if (labels.length <= 1) return labels.join("");
  return `${labels.slice(0, -1).join(", ")} e ${labels[labels.length - 1]}`;
}

export function skillEvidenceLine(skill: SkillResult): string | null {
  if (skill.skill === "writing" && skill.status === "provisional") {
    const samples = Math.max(skill.evidence_counts?.answered ?? 1, 1);
    return countLabel(samples, "produção escrita avaliada", "produções escritas avaliadas");
  }
  if (skill.skill === "speaking" && skill.status === "provisional") {
    const samples = Math.max(skill.evidence_counts?.answered ?? 1, 1);
    return countLabel(samples, "amostra de fala avaliada", "amostras de fala avaliadas");
  }
  if (skill.skill === "writing" || skill.skill === "speaking") return null;
  if (skill.score == null || skill.max_score == null || skill.max_score <= 0) return null;
  const hits = Math.round(skill.score);
  const total = Math.round(skill.max_score);
  return `${countLabel(hits, "acerto", "acertos")} em ${countLabel(total, "questão", "questões")}`;
}

export function planningRecommendation(level: string): string {
  return `Nível recomendado para iniciar sua jornada: ${levelShortCode(level) ?? level}`;
}

export function journeyStartLabel(level: string): string {
  return `Começar minha jornada em ${levelShortCode(level) ?? level}`;
}

export function journeyDestination(
  curriculum: { day_href?: string | null } | null | undefined,
): string | null {
  const href = curriculum?.day_href?.trim();
  return href ? href : null;
}

/** Proposta deste assessment diferente da entrada que ficou aplicada. */
export function retainedPlanning(result: {
  planning_level?: string | null;
  planning_level_trace?: { assessment_proposed_level?: string | null } | null;
}): { applied: string; proposed: string } | null {
  const applied = result.planning_level;
  const proposed = result.planning_level_trace?.assessment_proposed_level;
  if (!applied || !proposed || proposed === applied) return null;
  return { applied, proposed };
}

export function retainedPlanningNote(applied: string, proposed: string): string {
  const appliedCode = levelShortCode(applied) ?? applied;
  const proposedCode = levelShortCode(proposed) ?? proposed;
  return `Este teste propôs ${proposedCode}. A entrada aplicada é ${appliedCode}, porque o planejamento anterior foi mantido.`;
}

export function priorityReasonLabel(reason: string, hasOverall: boolean): string {
  if (reason === "below_overall" || reason === "needs_practice") {
    return hasOverall ? " — abaixo do nível geral" : " — precisa de prática";
  }
  if (reason === "lowest_accuracy") return " — menor acurácia recente";
  return " — precisa de mais evidência";
}

export type CollectionEnding = { title: string; detail: string | null };

/** Encerramento conforme o motivo do backend; esgotamento e skip não são sucesso. */
export function collectionEnding(
  stopReason: string | null | undefined,
  coverage?: AssessmentCoverage | null,
): CollectionEnding {
  const unsatisfied = coverageSkillsInOrder(coverage).filter(({ entry }) => !entry.satisfied);
  const skipped = unsatisfied.filter(({ entry }) => entry.skipped || (entry.reason != null && SKIP_REASONS.has(entry.reason)));
  const skippedNames = listSkills(skipped.map(({ skill }) => skill));

  if (stopReason === "bank_exhausted" || stopReason === "bank_freshness_exhausted") {
    const affected = unsatisfied.filter(({ entry }) => !entry.skipped).map(({ skill }) => skill);
    const parts = [
      affected.length ? `Não foi possível completar: ${listSkills(affected)}.` : null,
      skippedNames ? `Não avaliada por escolha sua: ${skippedNames}.` : null,
      "Seu perfil será parcial.",
    ].filter(Boolean);
    return {
      title: "Não há mais atividades adequadas disponíveis para completar esta competência nesta sessão.",
      detail: parts.join(" "),
    };
  }
  if (stopReason === "maximum_reached") {
    return {
      title: "A avaliação atingiu o limite desta sessão.",
      detail: skippedNames
        ? `O perfil abaixo usa as evidências coletadas. Não avaliada: ${skippedNames}.`
        : "O perfil abaixo usa as evidências coletadas.",
    };
  }
  if (stopReason != null && SKIP_REASONS.has(stopReason)) {
    return {
      title: "Coleta encerrada sem avaliar todas as competências.",
      detail: skippedNames
        ? `Não avaliada nesta sessão: ${skippedNames}. O perfil abaixo usa as evidências coletadas.`
        : "Uma competência não foi avaliada nesta sessão. O perfil abaixo usa as evidências coletadas.",
    };
  }
  if (coverage && coverage.mandatory_complete === false && (unsatisfied.length || skippedNames)) {
    return {
      title: "Coleta encerrada sem avaliar todas as competências.",
      detail: skippedNames
        ? `Não avaliada nesta sessão: ${skippedNames}. O perfil abaixo usa as evidências coletadas.`
        : `Não foi possível completar: ${listSkills(unsatisfied.map(({ skill }) => skill))}. O perfil abaixo usa as evidências coletadas.`,
    };
  }
  return { title: "Coleta concluída.", detail: "As evidências previstas foram reunidas." };
}
