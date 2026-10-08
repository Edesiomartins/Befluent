import type { CefrLevel, LevelSource, Skill } from "@/lib/levels";

export type PlacementProgress = {
  activities_completed?: number;
  activities_skipped?: number;
  by_skill?: Partial<Record<Skill, { completed: number }>>;
  stop_reason?: string | null;
  answered: number;
  minimum: number;
  target: number;
  maximum: number;
  writing_submitted: boolean;
};

export type PlacementTest = {
  id: string;
  language_code: string;
  status: "pending" | "in_progress" | "completed" | "abandoned";
  version: number;
  source: string;
  started_at: string | null;
  completed_at: string | null;
  progress: PlacementProgress;
  speaking_available: boolean;
};

export type PlacementItem = {
  exposure?: { reused: boolean; previous_exposure_count: number; exposure_status: string; evidence_eligible: boolean };
  id: string;
  skill: Skill;
  skill_label: string;
  item_type: string;
  prompt: string;
  instructions: string | null;
  passage: string | null;
  options: string[];
  audio_url: string | null;
  audio_script: string | null;
};

export type NextItemResponse = {
  item: PlacementItem | null;
  stage: "objective" | "writing" | "speaking" | "ready_to_complete";
  progress: PlacementProgress;
};

export type LevelDetails = {
  code: CefrLevel;
  name_pt: string;
  short_description: string;
  order_index: number;
  testable: boolean;
};

export type SkillResult = {
  skill: Skill;
  label: string;
  estimated_level: CefrLevel | null;
  level: LevelDetails | null;
  score: number | null;
  max_score: number | null;
  status: "assessed" | "calibrating" | "not_assessed" | "not_available" | "estimated" | "provisional" | "insufficient_evidence" | "not_collected" | "unavailable";
  evidence_counts?: { answered: number; valid: number; excluded: number; by_cefr: Record<string, number> };
  skill_confidence?: { basis: string; label: string; reasons: string[] };
};

export type Recommendation = {
  skill: Skill;
  reason: "below_overall" | "not_assessed" | "insufficient_evidence" | "needs_practice" | "lowest_accuracy";
  priority: number;
  href?: string;
};

export type PlanningLevelTrace = {
  action?: string;
  assessment_proposed_level?: string | null;
  retained_global_level?: string | null;
};

export type PlacementResult = {
  profile_status?: "partial" | "complete";
  planning_level?: string | null;
  planning_level_source?: string | null;
  planning_level_reason?: string | null;
  planning_level_trace?: PlanningLevelTrace | null;
  overall_estimate_status?: "partial" | "sufficient";
  assessment_coverage?: { missing_skills: Skill[]; stop_reason?: string; reused_evidence?: number };
  id: string;
  language_code: string;
  status: string;
  completed_at: string | null;
  duration_seconds: number | null;
  overall_level: CefrLevel | null;
  overall: LevelDetails | null;
  confidence_score: number | null;
  confidence_label: string | null;
  diagnostic_status: "ready" | "calibrating";
  items_answered: number | null;
  weights_used: Record<string, number>;
  recommendations: Recommendation[];
  priority_focus: Recommendation[];
  skills: SkillResult[];
  speaking_available: boolean;
  disclaimer: string;
  curriculum?: {
    id: string;
    duration_days: number;
    entry_level: string;
    target_level: string;
    day_href: string;
    generated_from?: string;
    entry_level_source?: string;
  } | null;
};

export type DashboardLevel = {
  last_assessment_id?: string | null;
  assessment_status?: "partial" | "sufficient" | null;
  current_level: CefrLevel | null;
  details: LevelDetails | null;
  source: LevelSource;
  from_test: boolean;
  assessed_at: string | null;
  confidence_score: number | null;
  confidence_label: string | null;
  placement_test_id: string | null;
  skills: { skill: Skill; label: string; estimated_level: CefrLevel | null }[];
  recommendations: Recommendation[];
  needs_placement_test: boolean;
};
