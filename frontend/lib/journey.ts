/**
 * BeFluent Journey — apresentação sobre o cronograma existente.
 * Não persiste missão: título, progresso e fases saem de week/day/blocks.
 */

import type { CurriculumBlock, CurriculumDay, LessonPhase } from "@/types/curriculum";

export type MissionStatus = "pending" | "in_progress" | "completed";

export type DailyMission = {
  title: string;
  subtitle: string;
  scenario: string;
  learner_goal: string;
  language_name: string;
  level: string;
  estimated_minutes: number;
  progress_current: number;
  progress_total: number;
  status: MissionStatus;
  day_id: string;
  day_number: number;
  phases: Array<{
    key: string;
    label: string;
    state: "done" | "current" | "upcoming";
  }>;
};

/** Rótulos da jornada para o aluno. Enums internos permanecem. */
export const JOURNEY_PHASE_LABELS: Record<LessonPhase, string> = {
  activate: "Preparar",
  structure: "Descobrir",
  input: "Compreender",
  output: "Usar",
  consolidate: "Consolidar",
};

export function journeyPhaseLabel(phase: string | undefined, fallback?: string): string {
  if (phase && phase in JOURNEY_PHASE_LABELS) {
    return JOURNEY_PHASE_LABELS[phase as LessonPhase];
  }
  return fallback || "Etapa";
}

function clean(value: string | null | undefined): string {
  return (value || "").replace(/\s+/g, " ").trim();
}

/** Título situacional: objetivo do aluno → tópico do bloco → tema da semana → dia. */
export function missionTitle(day: CurriculumDay, weekTheme?: string | null): string {
  const goal = clean(day.learning_objective?.learner_goal);
  if (goal && !/^dia\s+\d+/i.test(goal)) return goal;
  const topic = clean(day.blocks.find((block) => clean(block.topic))?.topic);
  if (topic && !/^dia\s+\d+/i.test(topic)) return topic;
  const theme = clean(weekTheme);
  if (theme) return theme;
  return `Dia ${day.day_number}`;
}

export function missionStatus(day: CurriculumDay): MissionStatus {
  if (day.status === "completed" || (day.blocks_total > 0 && day.blocks_completed >= day.blocks_total)) {
    return "completed";
  }
  if (day.status === "in_progress" || day.blocks_completed > 0) return "in_progress";
  return "pending";
}

export function missionCta(status: MissionStatus): string {
  if (status === "completed") return "Missão concluída";
  if (status === "in_progress") return "Continuar missão";
  return "Começar missão";
}

function phaseState(
  block: CurriculumBlock,
  index: number,
  blocks: CurriculumBlock[],
): "done" | "current" | "upcoming" {
  if (block.status === "completed") return "done";
  const firstOpen = blocks.findIndex((item) => item.status !== "completed");
  if (block.is_current || index === firstOpen) return "current";
  return "upcoming";
}

export function deriveDailyMission(input: {
  day: CurriculumDay;
  weekTheme?: string | null;
  languageName: string;
  level?: string | null;
}): DailyMission {
  const { day } = input;
  const title = missionTitle(day, input.weekTheme);
  const goal =
    clean(day.learning_objective?.learner_goal) ||
    clean(input.weekTheme) ||
    "Praticar o conteúdo deste dia no seu ritmo.";
  const subtitle = goal === title ? clean(input.weekTheme) || goal : goal;
  const level =
    clean(input.level) ||
    clean(day.learning_objective?.level) ||
    clean(day.blocks[0]?.cefr_level) ||
    "";
  return {
    title,
    subtitle,
    scenario: title,
    learner_goal: goal,
    language_name: input.languageName,
    level,
    estimated_minutes: day.total_minutes,
    progress_current: day.blocks_completed,
    progress_total: day.blocks_total,
    status: missionStatus(day),
    day_id: day.id,
    day_number: day.day_number,
    phases: day.blocks.map((block, index) => ({
      key: block.id,
      label: journeyPhaseLabel(block.phase, block.phase_label),
      state: phaseState(block, index, day.blocks),
    })),
  };
}

/** Tópico enviado à conversação quando a prática nasce da missão. */
export function conversationTopic(input: {
  lessonSituation?: string | null;
  missionScenario?: string | null;
  freePractice?: boolean;
}): string {
  if (input.freePractice) {
    const own = clean(input.lessonSituation);
    return own || "Conversa livre";
  }
  const situation = clean(input.lessonSituation);
  if (situation && situation.toLowerCase() !== "conversa livre") return situation;
  return clean(input.missionScenario) || situation || "Conversa livre";
}
