/** Constantes de marca — BeFluent */
export const BRAND = {
  name: "BeFluent",
  slogan: "Aprenda. Pratique. Fale.",
  description:
    "Seu tutor inteligente para aprender idiomas e desenvolver fluência no seu ritmo.",
  institutional: "Uma plataforma MedQuestHub AI",
  poweredBy: "Powered by MedQuestHub AI",
  domain: "befluent.medquesthub.com.br",
  apiDomain: "api-befluent.medquesthub.com.br",
} as const;

export const LANGUAGES = [
  { code: "en", namePt: "Inglês", native: "English" },
  { code: "es-ES", namePt: "Espanhol da Espanha", native: "Español" },
  { code: "fr", namePt: "Francês", native: "Français" },
  { code: "ja", namePt: "Japonês", native: "日本語" },
  { code: "zh-CN", namePt: "Mandarim", native: "中文" },
] as const;
