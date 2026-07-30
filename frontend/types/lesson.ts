/** Contratos da API de lições adaptadas (POST /api/v1/lessons/generate). */

export type LessonEnvelope = {
  mode: string;
  provider: "mock" | "openrouter";
  language_code: string;
  /** Nível usado para calibrar esta lição (da competência, quando avaliada). */
  level: string;
  overall_level: string;
  skill: string | null;
  skill_label: string | null;
  level_source: string;
  level_is_estimated: boolean;
  lesson_id?: string;
  study_session_id?: string;
  title: string;
  objective: string;
};

export type VocabularyLesson = LessonEnvelope & {
  items: Array<{
    term: string;
    translation: string;
    example: string;
    example_translation: string;
    usage_note: string;
  }>;
};

export type GrammarLesson = LessonEnvelope & {
  explanation: string;
  patterns: string[];
  examples: Array<{ sentence: string; translation: string }>;
  exercises: Array<{
    prompt: string;
    options: string[];
    answer: string;
    rationale: string;
  }>;
};

export type ReadingLesson = LessonEnvelope & {
  text: string;
  note?: string;
  glossary: Array<{ term: string; translation: string }>;
  questions: Array<{ prompt: string; options: string[]; answer: string }>;
};

export type ListeningLesson = LessonEnvelope & {
  transcript: string;
  speaking_rate: string;
  note?: string;
  questions: Array<{ prompt: string; options: string[]; answer: string }>;
};

export type WritingLesson = LessonEnvelope & {
  prompt: string;
  min_words: number;
  max_words: number;
  rubric_hints: string[];
  useful_expressions: string[];
};

export type ConversationLesson = LessonEnvelope & {
  situation: string;
  opening: string;
  opening_translation: string;
  suggested_replies: string[];
  target_expressions: string[];
};

export type PronunciationLesson = LessonEnvelope & {
  focus_sounds: Array<{ sound: string; why_hard: string; how_to_produce: string }>;
  target_phrases: Array<{ phrase: string; translation: string; focus: string }>;
};

export type GuidedLesson = LessonEnvelope & {
  steps: Array<{
    title: string;
    explanation: string;
    example: string;
    example_translation: string;
  }>;
  check_question: string;
};

export type ReviewLesson = LessonEnvelope & {
  items: Array<{ prompt: string; answer: string; hint: string }>;
};

export type LessonModesResponse = {
  language_code: string;
  level: string;
  level_source: string;
  level_is_estimated: boolean;
  weakest_skills: Array<{ skill: string; label: string }>;
  recommended_modes: string[];
  modes: Array<{
    mode: string;
    skill: string | null;
    skill_label: string | null;
    level: string;
    recommended: boolean;
  }>;
};

/** Devolutiva da correção de escrita (POST /api/v1/writing). */
export type WritingFeedback = {
  id: string | null;
  status: "assessed" | "not_evaluated";
  evaluated_by: "ai" | "heuristic";
  normalized_score?: number;
  score?: number | null;
  target_level?: string;
  estimated_level?: string;
  word_count: number;
  min_words: number;
  max_words: number;
  within_range: boolean;
  criteria: Array<{ key: string; label: string; score: number }>;
  feedback?: string;
  notice?: string;
  reason?: string;
  metrics?: {
    chars: number;
    tokens: number;
    sentences: number;
    lexical_diversity: number;
  };
};
