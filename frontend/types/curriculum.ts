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

/** Item de léxico que atravessa os blocos do dia. */
export type ThreadTerm = {
  term: string;
  translation: string;
  example: string;
  example_translation: string;
};

/**
 * Fio condutor — espelha `backend/app/services/lesson_thread.py`.
 * É o material que um bloco entrega ao seguinte: sem ele o dia seriam cinco
 * lições soltas debaixo do mesmo tema.
 */
export type LessonThread = {
  terms: ThreadTerm[];
  patterns: string[];
  /** Rótulos dos blocos de origem, na ordem estudada. */
  sources: string[];
};

/** Continuidade declarada dentro da lição (`ai.py::_envelope`). */
export type LessonThreadRef = {
  carried_terms: string[];
  carried_patterns: string[];
  sources: string[];
  recycled_terms: string[];
  /** `false` em conteúdo curado ou de IA: a continuidade foi pedida, não garantida. */
  guaranteed: boolean;
};

/** Próxima jornada do currículo — liberada ao concluir o dia atual. */
export type NextDayRef = {
  id: string;
  day_number: number;
  available: boolean;
  scheduled_date: string;
  status: DayStatus;
};

export type PaceStatus = "ahead" | "on_track" | "behind";

export type CurriculumDay = {
  id: string;
  day_number: number;
  /** Data recomendada de ritmo — nunca bloqueia acesso. */
  scheduled_date: string;
  status: DayStatus;
  completed_at: string | null;
  total_minutes: number;
  blocks_total: number;
  blocks_completed: number;
  sequence_label?: string;
  current_block_id?: string | null;
  thread?: LessonThread | null;
  blocks: CurriculumBlock[];
  next_day?: NextDayRef | null;
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
  /** Ritmo vs. datas recomendadas — informativo, nunca bloqueante. */
  pace_status?: PaceStatus;
  pace_delta?: number;
  pace_label_pt?: string;
  recommended_by_schedule?: number;
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
  /** Item que entrou na fila hoje, pelos blocos anteriores deste dia. */
  from_today?: boolean;
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
  from_today_count?: number;
  items?: ReviewQueueItem[];
  thread?: LessonThreadRef | null;
  thread_note?: string | null;
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
  /** Palavras deste bloco que entraram na fila de revisão espaçada. */
  review_items_added?: number;
  progress: CurriculumProgress;
  next_day?: NextDayRef | null;
};
