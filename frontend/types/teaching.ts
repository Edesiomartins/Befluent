export type TeachingFlowPhase =
  | "not_started"
  | "activating"
  | "input"
  | "noticing"
  | "practicing"
  | "producing"
  | "evaluating"
  | "needs_remediation"
  | "retrying"
  | "transfer_check"
  | "mastered"
  | "needs_review";

export type AnswerFeedback = {
  is_correct: boolean;
  selected: string;
  correct_option: string;
  selected_label?: string;
  correct_label?: string;
  why_selected?: string | null;
  why_correct?: string | null;
  remember?: string | null;
};

export type TeachingActivity = {
  index?: number;
  type: string;
  phase_hint?: string;
  prompt?: string;
  prompt_pt?: string;
  title_pt?: string;
  can_do?: string;
  models?: string[];
  examples?: string[];
  show_text?: boolean;
  tokens?: string[];
  options?: string[];
  pairs?: { term: string; hint_pt: string }[];
  canonical_answer?: string;
  accepted_variants?: string[];
  required_features?: string[];
  scaffold_pt?: string;
  ai_required?: boolean;
  post_reveal?: boolean;
  is_retry_variant?: boolean;
};

export type SliceSession = {
  flow: {
    id: string;
    phase: TeachingFlowPhase;
    phase_label_pt: string;
    status: string;
    activity_cursor: number;
    remediation_cycles: number;
  };
  objective: {
    id: string;
    code: string | null;
    title: string | null;
    can_do: string | null;
    level: string | null;
  };
  progress_state: string;
  current_activity: TeachingActivity | null;
  activities_total: number;
  attempt?: {
    id: string;
    result: string;
    attempt_number: number;
  };
  evaluation?: {
    result: string;
    evaluation_method: string;
    ai_called: boolean;
    details?: Record<string, unknown>;
  } | null;
  remediation?: {
    id: string;
    action: string;
    error_id: string;
    explanation?: string | null;
    contrast?: { incorrect: string; correct?: string | null };
    hint_pt?: string;
    answer_feedback?: AnswerFeedback | null;
  } | null;
  answer_feedback?: AnswerFeedback | null;
  activity_locked?: boolean;
  mastery?: {
    state: string;
    reasons: string[];
    memory_schedule_id?: string | null;
  };
  ai_called?: boolean;
};
