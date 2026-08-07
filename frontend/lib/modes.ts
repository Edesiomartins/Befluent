import {
  AudioLines,
  BookOpen,
  ClipboardCheck,
  GraduationCap,
  Headphones,
  MessagesSquare,
  Mic,
  PenLine,
  RotateCcw,
  SpellCheck2,
  Volume2,
  type LucideIcon,
} from "lucide-react";

export type ModeColor = "primary" | "success" | "streak" | "gold" | "violet" | "teal" | "rose";

export type ModeMeta = {
  slug: string;
  title: string;
  description: string;
  duration: string;
  icon: LucideIcon;
  color: ModeColor;
};

export const MODES: ModeMeta[] = [
  { slug: "guided", title: "Aula guiada", description: "Uma sequência estruturada de explicação e prática.", duration: "20 min", icon: GraduationCap, color: "teal" },
  { slug: "conversation", title: "Conversação", description: "Dialogue por texto com correções no momento certo.", duration: "15 min", icon: MessagesSquare, color: "primary" },
  { slug: "voice", title: "Conversa por voz", description: "Treine fala, transcrição e compreensão oral.", duration: "10 min", icon: Mic, color: "violet" },
  { slug: "pronunciation", title: "Pronúncia", description: "Pratique fala com modelo e transcrição — sem nota fonética inventada.", duration: "10 min", icon: Volume2, color: "streak" },
  { slug: "vocabulary", title: "Vocabulário", description: "Amplie e consolide palavras em contexto.", duration: "12 min", icon: BookOpen, color: "gold" },
  { slug: "grammar", title: "Gramática", description: "Estude estruturas a partir de situações reais.", duration: "15 min", icon: SpellCheck2, color: "rose" },
  { slug: "listening", title: "Compreensão auditiva", description: "Ouça, interprete e confira seu entendimento.", duration: "12 min", icon: Headphones, color: "success" },
  { slug: "reading", title: "Leitura", description: "Leia textos adequados ao seu nível com apoio.", duration: "15 min", icon: AudioLines, color: "violet" },
  { slug: "writing", title: "Escrita", description: "Produza textos e entenda cada correção.", duration: "20 min", icon: PenLine, color: "rose" },
  { slug: "review", title: "Revisão", description: "Retome itens agendados pelo seu progresso.", duration: "8 min", icon: RotateCcw, color: "gold" },
  { slug: "assessment", title: "Diagnóstico", description: "Atualize a estimativa do seu nível.", duration: "25 min", icon: ClipboardCheck, color: "primary" },
];

export function getMode(slug: string): ModeMeta | undefined {
  return MODES.find((mode) => mode.slug === slug);
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
