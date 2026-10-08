import { levelShortCode, type Skill } from "@/lib/levels";
import type { PlacementResult, SkillResult } from "@/types/placement";

const SKILL_ORDER: Skill[] = [
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

export function skillBandLabel(skill: SkillResult): string {
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

function confirmationGap(skill: SkillResult): number | null {
  if (typeof skill.confirmation_needed === "number") return skill.confirmation_needed;
  if (typeof skill.confirmation_required === "number" && typeof skill.confirmation_count === "number") {
    return Math.max(skill.confirmation_required - skill.confirmation_count, 0);
  }
  return null;
}

export function skillConfirmationNote(skill: SkillResult): string | null {
  if (skill.status !== "insufficient_evidence" || !skill.candidate_level) return null;
  const level = levelCode(skill.candidate_level);
  const needed = confirmationGap(skill);
  if (needed === 1) {
    return `Falta mais uma atividade ${level} independente para confirmar esta faixa.`;
  }
  if (needed != null && needed > 1) {
    return `Faltam mais ${needed} atividades ${level} independentes para confirmar esta faixa.`;
  }
  const reason = skill.candidate_reason?.trim();
  if (reason && !/^[a-z0-9_]+$/.test(reason)) return reason;
  return null;
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

export function collectionEnding(stopReason: string | null | undefined): string {
  if (stopReason === "bank_exhausted" || stopReason === "bank_freshness_exhausted") {
    return "A coleta foi encerrada porque não há mais atividades inéditas adequadas disponíveis. Você receberá um perfil parcial.";
  }
  if (stopReason === "maximum_reached") {
    return "A coleta atingiu o limite desta sessão. Vamos apresentar as evidências disponíveis.";
  }
  return "Coleta concluída. As evidências previstas foram reunidas.";
}
