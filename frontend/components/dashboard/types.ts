import type { LanguageProgress } from "@/components/language-progress-panel";
import type { DashboardLevel } from "@/types/placement";

export type DashboardData = {
  onboarding_completed: boolean;
  active_language: {
    code: string;
    name_pt: string;
    native_name: string;
    level_estimate: string | null;
    goal: string | null;
    minutes_per_day: number | null;
    skills: string[];
    onboarding_completed: boolean;
    user_language_id: string;
    level?: DashboardLevel;
  } | null;
  next_activity: {
    title: string;
    description: string;
    href: string;
    cta: string;
    kind: string;
  };
  day_plan: {
    minutes_per_day: number | null;
    goal: string | null;
    skills: string[];
    items: Array<{ label: string; done: boolean }>;
  };
  progress: {
    vocabulary_items: number;
    study_sessions: number;
    reviews_due_count: number;
    streak_days: number;
    total_minutes?: number;
    minutes_today?: number;
    total_minutes_label?: string;
  };
  reviews_due_count: number;
  reviews_due: Array<{
    id: string;
    item_type: string;
    reference_id: string;
    payload: Record<string, unknown>;
    next_review_at: string | null;
  }>;
  recent_activity: Array<{
    id: string;
    status: string;
    summary: string | null;
    started_at: string | null;
    ended_at: string | null;
    minutes?: number;
  }>;
  language_progress?: LanguageProgress | null;
};

export const practiceSlugs = ["voice", "vocabulary", "review", "guided", "listening", "writing"];
