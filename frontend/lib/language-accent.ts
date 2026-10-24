export const LANGUAGE_CODES = ["en", "es-ES", "fr", "it", "de", "ja", "zh-CN", "la"] as const;

export type TargetLanguageCode = (typeof LANGUAGE_CODES)[number];

export type LanguageAccent = { ink: string; soft: string };

/** Tinta escura sobre branco: cada par passa contraste AA (4.5:1) no teste. */
export const LANGUAGE_ACCENTS: Record<TargetLanguageCode, LanguageAccent> = {
  en: { ink: "#1d4ed8", soft: "#dbeafe" },
  "es-ES": { ink: "#9a3412", soft: "#ffedd5" },
  fr: { ink: "#1e3a8a", soft: "#dbeafe" },
  it: { ink: "#9f1239", soft: "#ffe4e6" },
  de: { ink: "#134e4a", soft: "#ccfbf1" },
  ja: { ink: "#5b21b6", soft: "#ede9fe" },
  "zh-CN": { ink: "#7f1d1d", soft: "#fee2e2" },
  la: { ink: "#3f6212", soft: "#ecfccb" },
};

export function accentFor(code: string | null | undefined): LanguageAccent {
  if (code && code in LANGUAGE_ACCENTS) return LANGUAGE_ACCENTS[code as TargetLanguageCode];
  return LANGUAGE_ACCENTS.en;
}
