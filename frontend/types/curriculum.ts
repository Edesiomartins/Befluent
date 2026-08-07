/** Cronograma estruturado — espelha `backend/app/api/curriculum.py`. */

import type { CefrLevel } from "@/lib/levels";

export type BlockSkill =
  | "vocabulary"
  | "grammar"
  | "pronunciation"
  | "listening"
  | "reading"
  | "conversation"
  | "writing"
  | "review";

export type BlockStatus = "pending" | "completed";
export type DayStatus = "pending" | "in_progress" | "completed" | "skipped";
export type CurriculumStatus = "active" | "paused" | "completed" | "regenerated";

/** Durações oferecidas ao aluno. Espelha `ALLOWED_DURATIONS` no backend. */
export const DURATIONS = [90, 180] as const;
export type Duration = (typeof DURATIONS)[number];

export type LessonPhase =
  | "activate"
  | "structure"
  | "input"
  | "output"
  | "consolidate";

export type CurriculumBlock = {
  id: string;
  skill: BlockSkill;
  skill_label: string;
  /** Modo de estudo correspondente em `lib/modes.ts`. */
  mode: string | null;
  position: number;
  estimated_minutes: number;
  cefr_level: CefrLevel;
  topic: string;
  lesson_ref: string | null;
  status: BlockStatus;
  score: number | null;
  phase?: LessonPhase;
  phase_label?: string;
  phase_why?: string;
  locked?: boolean;
  is_current?: boolean;
};

export type CurriculumDay = {
  id: string;
  day_number: number;
  scheduled_date: string;
  status: DayStatus;
  completed_at: string | null;
  total_minutes: number;
  blocks_total: number;
  blocks_completed: number;
  sequence_label?: string;
  current_block_id?: string | null;
  blocks: CurriculumBlock[];
};

export type CurriculumWeek = {
  id: string;
  week_number: number;
  theme: string;
  cefr_focus: CefrLevel;
  is_checkpoint: boolean;
  days?: CurriculumDay[];
};

export type CurriculumProgress = {
  days_total: number;
  days_completed: number;
  percent_complete: number;
  current_day_number: number | null;
  overdue_days: number;
  needs_reschedule: boolean;
  next_checkpoint_week: number | null;
};

export type LevelDetails = {
  code: CefrLevel;
  name_pt: string;
  short_description: string;
  order_index: number;
  testable: boolean;
};

export type Curriculum = {
  id: string;
  duration_days: number;
  start_date: string;
  entry_level: CefrLevel;
  target_level: CefrLevel;
  entry: LevelDetails;
  target: LevelDetails;
  status: CurriculumStatus;
  generated_from: string;
  weeks_total: number;
  disclaimer: string;
  progress?: CurriculumProgress;
};

export type ActiveCurriculum = Curriculum & {
  progress: CurriculumProgress;
  weeks: CurriculumWeek[];
};

export type OverdueDay = {
  id: string;
  day_number: number;
  scheduled_date: string;
};

export type TodayPayload = {
  curriculum: Curriculum & { progress: CurriculumProgress };
  week: CurriculumWeek | null;
  day: CurriculumDay | null;
  overdue_days: OverdueDay[];
};

export type DayDetail = {
  curriculum: Curriculum;
  week: CurriculumWeek;
  day: CurriculumDay;
};

export type RescheduleStrategy = "compress" | "extend";

/** Item vencido da fila do SRS, servido pelo bloco de revisão. */
export type ReviewQueueItem = {
  review_item_id: string;
  item_type: string;
  reference_id: string;
  payload: Record<string, unknown>;
  next_review_at: string | null;
};

/** Lição do bloco. O formato varia por modo; só o envelope é garantido. */
export type BlockLesson = {
  lesson_id?: string;
  study_session_id?: string;
  title: string;
  objective?: string;
  topic?: string;
  level?: string;
  provider?: string;
  mode?: string;
  source?: string;
  queue_empty?: boolean;
  empty_notice?: string | null;
  items?: ReviewQueueItem[];
  [key: string]: unknown;
};

export type StartBlockResponse = {
  block: CurriculumBlock;
  lesson: BlockLesson;
};

export type CompleteBlockResponse = {
  block: CurriculumBlock;
  day: { id: string; status: DayStatus; completed_at: string | null };
  day_completed: boolean;
  progress: CurriculumProgress;
};
