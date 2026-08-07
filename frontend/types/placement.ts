import type { CefrLevel, LevelSource, Skill } from "@/lib/levels";

export type PlacementProgress = {
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
  stage: "objective" | "writing" | "ready_to_complete";
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
  score: number;
  max_score: number;
  status: "assessed" | "not_assessed" | "not_available";
};

export type Recommendation = {
  skill: Skill;
  reason: "below_overall" | "not_assessed";
  priority: number;
};

export type PlacementResult = {
  id: string;
  language_code: string;
  status: string;
  completed_at: string | null;
  duration_seconds: number | null;
  overall_level: CefrLevel | null;
  overall: LevelDetails | null;
  confidence_score: number | null;
  confidence_label: string | null;
  items_answered: number | null;
  weights_used: Record<string, number>;
  recommendations: Recommendation[];
  skills: SkillResult[];
  speaking_available: boolean;
  disclaimer: string;
  curriculum?: {
    id: string;
    duration_days: number;
    entry_level: string;
    target_level: string;
    day_href: string;
  } | null;
};

export type DashboardLevel = {
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
