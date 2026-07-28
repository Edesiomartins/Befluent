/** Níveis CEFR e competências — espelha `backend/app/core/levels.py`. */

export const CEFR_LEVELS = ["PRE_A1", "A1", "A2", "B1", "B2", "C1", "C2"] as const;

export type CefrLevel = (typeof CEFR_LEVELS)[number];

export type Skill =
  | "vocabulary_grammar"
  | "reading"
  | "listening"
  | "writing"
  | "speaking";

export type LevelSource =
  | "placement_test"
  | "self_declared"
  | "self_declared_beginner"
  | "admin"
  | "imported"
  | "pending";

export const LEVEL_DETAILS: Record<CefrLevel, { name: string; description: string }> = {
  PRE_A1: {
    name: "Pré-A1 — Primeiros passos",
    description: "Reconhece palavras, cumprimentos e expressões muito básicas.",
  },
  A1: {
    name: "A1 — Iniciante",
    description:
      "Consegue se apresentar, fornecer informações pessoais e compreender frases simples.",
  },
  A2: {
    name: "A2 — Básico",
    description: "Comunica-se em situações rotineiras e compreende mensagens frequentes.",
  },
  B1: {
    name: "B1 — Intermediário",
    description: "Mantém conversas sobre temas familiares e relata experiências.",
  },
  B2: {
    name: "B2 — Intermediário avançado",
    description: "Interage com boa espontaneidade e compreende conteúdos mais complexos.",
  },
  C1: {
    name: "C1 — Avançado",
    description:
      "Usa o idioma com flexibilidade em contextos acadêmicos, sociais e profissionais.",
  },
  C2: {
    name: "C2 — Domínio",
    description:
      "Compreende praticamente tudo e se expressa com grande precisão e naturalidade.",
  },
};

export const SKILL_LABELS: Record<Skill, string> = {
  vocabulary_grammar: "Vocabulário e gramática",
  reading: "Leitura",
  listening: "Compreensão auditiva",
  writing: "Escrita",
  speaking: "Fala",
};

export const LEVEL_SOURCE_LABELS: Record<LevelSource, string> = {
  placement_test: "Teste de nivelamento",
  self_declared: "Nível informado",
  self_declared_beginner: "Iniciante absoluto",
  admin: "Definido pela equipe",
  imported: "Importado",
  pending: "Ainda não definido",
};

export function levelName(code: string | null | undefined): string | null {
  if (!code) return null;
  return LEVEL_DETAILS[code as CefrLevel]?.name ?? code;
}

export function levelShortCode(code: string | null | undefined): string | null {
  if (!code) return null;
  return code === "PRE_A1" ? "Pré-A1" : code;
}

export function confidenceLabel(value: number | null | undefined): string | null {
  if (value == null) return null;
  if (value >= 70) return "alta";
  if (value >= 45) return "moderada";
  return "baixa";
}
