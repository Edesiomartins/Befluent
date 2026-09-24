/**
 * Coach persistente por idioma — identidade de apresentação, não um segundo tutor.
 * A conversa pedagógica continua no fluxo de conversação; o widget de dúvidas
 * permanece separado.
 */

export type CoachProfile = {
  language_code: string;
  display_name: string;
  short_role: string;
};

const COACHES: Record<string, CoachProfile> = {
  en: { language_code: "en", display_name: "Alex", short_role: "coach de inglês" },
  "es-ES": { language_code: "es-ES", display_name: "Lucía", short_role: "coach de espanhol" },
  fr: { language_code: "fr", display_name: "Camille", short_role: "coach de francês" },
  it: { language_code: "it", display_name: "Giulia", short_role: "coach de italiano" },
  de: { language_code: "de", display_name: "Jonas", short_role: "coach de alemão" },
  ja: { language_code: "ja", display_name: "Hana", short_role: "coach de japonês" },
  "zh-CN": { language_code: "zh-CN", display_name: "Mei", short_role: "coach de mandarim" },
  la: { language_code: "la", display_name: "Clara", short_role: "coach de latim eclesiástico" },
  "la-classical": {
    language_code: "la-classical",
    display_name: "Marcus",
    short_role: "coach de latim clássico",
  },
};

const FALLBACK: CoachProfile = {
  language_code: "generic",
  display_name: "Coach",
  short_role: "coach do seu idioma",
};

export function coachFor(languageCode: string | null | undefined): CoachProfile {
  if (!languageCode) return FALLBACK;
  return COACHES[languageCode] ?? { ...FALLBACK, language_code: languageCode };
}
