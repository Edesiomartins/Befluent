/** Apoio na língua nativa do aluno. O frontend não traduz. */

export type SupportVisibility = "prominent" | "discreet" | "spot" | "expandable" | "off";

const VISIBILITIES = new Set<SupportVisibility>([
  "prominent",
  "discreet",
  "spot",
  "expandable",
  "off",
]);

export function isPortugueseNative(code: string | null | undefined): boolean {
  if (!code) return false;
  const normalized = code.trim().toLowerCase();
  return normalized === "pt" || normalized.startsWith("pt-");
}

function clean(value: string | null | undefined): string | null {
  const text = value?.trim();
  return text ? text : null;
}

/**
 * Texto de apoio já entregue pelo backend.
 *
 * `native` é o apoio na língua nativa, sem idioma fixo no nome do campo.
 * `legacyPortuguese` (`translation_pt`, `prompt_pt`, …) só entra quando a
 * língua nativa é portuguesa ou ainda não foi declarada. Com outra língua
 * nativa, esse texto seria uma terceira língua.
 */
export function supportText(input: {
  nativeLanguage?: string | null;
  native?: string | null;
  legacyPortuguese?: string | null;
}): string | null {
  const native = clean(input.native);
  if (native) return native;
  const legacy = clean(input.legacyPortuguese);
  if (!legacy) return null;
  if (input.nativeLanguage == null || input.nativeLanguage.trim() === "") return legacy;
  if (isPortugueseNative(input.nativeLanguage)) return legacy;
  return null;
}

/**
 * O backend decide o quanto de apoio mostrar (`support_visibility`).
 * Sem esse metadado, o apoio fica discreto: visível, secundário, sem regra
 * percentual inventada a partir do CEFR.
 */
export function resolveSupportVisibility(value: string | null | undefined): SupportVisibility {
  if (value && VISIBILITIES.has(value as SupportVisibility)) return value as SupportVisibility;
  return "discreet";
}

/** O áudio do conteúdo-alvo usa só o texto na língua estudada. */
export function speechText(target: string | null | undefined): string {
  return target?.trim() ?? "";
}
