import {
  AudioLines,
  Brain,
  ClipboardCheck,
  GraduationCap,
  Headphones,
  Mic,
  PenLine,
  RotateCcw,
  SpellCheck2,
  Volume2,
  type LucideIcon,
} from "lucide-react";

export type ModeColor = "primary" | "success" | "streak" | "gold" | "violet" | "teal" | "rose";

/** Grupo do hub de Prática (`/learn`) — puramente de apresentação/roteamento,
 * não tem relação com fases do Teaching Engine (ACTIVATING/INPUT/...). */
export type ModeSection = "recommended" | "skill" | "assessment";

export const MODE_SECTION_LABEL: Record<ModeSection, string> = {
  recommended: "Recomendado",
  skill: "Pratique uma habilidade",
  assessment: "Avaliação",
};

export type ModeMeta = {
  slug: string;
  title: string;
  description: string;
  duration: string;
  icon: LucideIcon;
  color: ModeColor;
  section: ModeSection;
};

/**
 * Cards do hub de Prática. `slug` é a rota (`/learn/{slug}`) e pode ser um id
 * técnico legado que já não bate com o título — ex. `voice` é o modo que já
 * existia para conversação com áudio (situação + turnos via `/conversations`
 * + STT/TTS), e passou a ser o único card de "Conversação" do hub: o antigo
 * card "Conversa por voz" era esse mesmo modo, e o antigo card "Conversação"
 * (diálogo só por texto, `slug: "conversation"`) foi removido do hub para
 * não duplicar a mesma habilidade. A rota `/learn/conversation` continua
 * existindo — é usada pelo cronograma de 90 dias (`BlockSkill.CONVERSATION`
 * em `core/curriculum.py`, fora do escopo desta reorganização) e por quem
 * acessar a URL diretamente; só não aparece mais como card aqui.
 */
export const MODES: ModeMeta[] = [
  { slug: "guided", title: "Aula guiada", description: "Uma sequência estruturada de explicação e prática.", duration: "20 min", icon: GraduationCap, color: "teal", section: "recommended" },
  { slug: "review", title: "Revisão", description: "Revise o que precisa antes de esquecer.", duration: "8 min", icon: RotateCcw, color: "gold", section: "recommended" },

  { slug: "vocabulary", title: "Vocabulário", description: "Aprenda, relembre e use palavras em contexto.", duration: "10 min", icon: Brain, color: "gold", section: "skill" },
  { slug: "grammar", title: "Gramática", description: "Entenda estruturas e use-as em situações reais.", duration: "15 min", icon: SpellCheck2, color: "rose", section: "skill" },
  { slug: "voice", title: "Conversação", description: "Ouça e responda por voz em conversas reais.", duration: "15 min", icon: Mic, color: "violet", section: "skill" },
  { slug: "pronunciation", title: "Pronúncia", description: "Ouça, repita e torne sua fala mais clara.", duration: "10 min", icon: Volume2, color: "streak", section: "skill" },
  { slug: "listening", title: "Compreensão auditiva", description: "Ouça sem legenda e teste sua compreensão.", duration: "12 min", icon: Headphones, color: "success", section: "skill" },
  { slug: "reading", title: "Leitura", description: "Leia textos do seu nível e compreenda pelo contexto.", duration: "15 min", icon: AudioLines, color: "violet", section: "skill" },
  { slug: "writing", title: "Escrita", description: "Produza textos e entenda cada correção.", duration: "20 min", icon: PenLine, color: "rose", section: "skill" },

  { slug: "assessment", title: "Diagnóstico", description: "Atualize a estimativa do seu nível.", duration: "25 min", icon: ClipboardCheck, color: "primary", section: "assessment" },
];

export function getMode(slug: string): ModeMeta | undefined {
  return MODES.find((mode) => mode.slug === slug);
}

/**
 * O backend recomenda modos por slug técnico (`services/learner_context.py`)
 * e nunca recomenda `"voice"` — a mesma função já filtra esse slug de
 * propósito (era considerado duplicado de `"conversation"`). Como o card do
 * hub para essa habilidade agora usa `slug: "voice"`, este alias só serve
 * para casar visualmente uma recomendação de `"conversation"` com o card
 * certo — não altera nada no backend nem na lógica de recomendação em si.
 */
const RECOMMENDED_SLUG_ALIASES: Record<string, string> = { conversation: "voice" };

export function resolveRecommendedSlug(slug: string): string {
  return RECOMMENDED_SLUG_ALIASES[slug] ?? slug;
}

export const modeColorClasses: Record<ModeColor, { bg: string; text: string; ring: string }> = {
  primary: { bg: "bg-primary-soft", text: "text-primary", ring: "group-hover:border-primary" },
  success: { bg: "bg-[var(--success-soft)]", text: "text-success", ring: "group-hover:border-success" },
  streak: { bg: "bg-[var(--streak-soft)]", text: "text-[var(--streak)]", ring: "group-hover:border-[var(--streak)]" },
  gold: { bg: "bg-[var(--gold-soft)]", text: "text-[var(--gold-ink)]", ring: "group-hover:border-[var(--gold)]" },
  violet: { bg: "bg-[var(--violet-soft)]", text: "text-[var(--violet)]", ring: "group-hover:border-[var(--violet)]" },
  teal: { bg: "bg-[var(--teal-soft)]", text: "text-[var(--teal)]", ring: "group-hover:border-[var(--teal)]" },
  rose: { bg: "bg-[var(--rose-soft)]", text: "text-[var(--rose)]", ring: "group-hover:border-[var(--rose)]" },
};
