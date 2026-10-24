/**
 * Família de interação da atividade.
 *
 * O backend pode mandar `interaction_family`. Se não mandar, o tipo oficial
 * resolve a família. `unknown` explícito não vira texto livre. Ausência de
 * família e de tipo conhecido fica `unspecified` para o legado.
 */

export const FAMILY_BY_TYPE: Record<string, string> = {
  presentation: "presentation",
  review: "presentation",
  recognition: "choice",
  reverse_recognition: "choice",
  multiple_choice: "choice",
  listening_recognition: "audio_choice",
  listen: "audio_model",
  fill_gap: "inline_gap",
  word_order: "tap_order",
  matching: "pair_match",
  lexical_production: "recall",
  controlled_recall: "recall",
  recall: "recall",
  guided_production: "guided_input",
  free_production: "open_input",
  repeat: "speech_repeat",
  shadow: "speech_shadow",
  retell: "speech_retell",
  conversation_prompt: "dialogue",
  transfer_question: "transfer",
  dictation: "dictation",
};

export const RENDERER_FAMILIES = [
  "presentation",
  "choice",
  "audio_choice",
  "audio_model",
  "inline_gap",
  "tap_order",
  "pair_match",
  "recall",
  "guided_input",
  "open_input",
  "speech_repeat",
  "speech_shadow",
  "speech_retell",
  "dialogue",
  "transfer",
  "dictation",
] as const;

export type RendererFamily = (typeof RENDERER_FAMILIES)[number];

const RENDERER_SET = new Set<string>(RENDERER_FAMILIES);

export function resolveInteractionFamily(activity: {
  type?: string | null;
  interaction_family?: string | null;
}): string {
  const explicit = activity.interaction_family?.trim();
  if (explicit === "unknown") return "unknown";
  if (explicit && RENDERER_SET.has(explicit)) return explicit;
  if (explicit) return "unknown";
  const derived = FAMILY_BY_TYPE[activity.type ?? ""];
  return derived ?? "unspecified";
}

export function hasDedicatedRenderer(family: string): boolean {
  return RENDERER_SET.has(family);
}
