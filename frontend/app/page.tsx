import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Flame,
  Headphones,
  MessagesSquare,
  RotateCcw,
  TrendingUp,
  Volume2,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { BRAND, LANGUAGES } from "@/lib/brand";
import type { ModeColor } from "@/lib/modes";
import { modeColorClasses } from "@/lib/modes";

const benefits: { title: string; description: string; icon: typeof MessagesSquare; color: ModeColor }[] = [
  {
    title: "Conversação com IA",
    description: "Pratique diálogos reais com feedback claro e no seu nível.",
    icon: MessagesSquare,
    color: "primary",
  },
  {
    title: "Prática de pronúncia",
    description: "Treine a fala com apoio de áudio e correções objetivas.",
    icon: Volume2,
    color: "streak",
  },
  {
    title: "Vocabulário contextual",
    description: "Salve e revise palavras no contexto em que aparecem.",
    icon: BookOpen,
    color: "gold",
  },
  {
    title: "Compreensão auditiva",
    description: "Escute, entenda e evolua a percepção natural do idioma.",
    icon: Headphones,
    color: "success",
  },
  {
    title: "Revisão inteligente",
    description: "Revise no momento certo com um agendador simples e substituível.",
    icon: RotateCcw,
    color: "violet",
  },
  {
    title: "Acompanhamento de progresso",
    description: "Veja evolução, sequência de estudos e próximos passos.",
    icon: TrendingUp,
    color: "teal",
  },
];

const steps = [
  "Crie sua conta",
  "Escolha o idioma",
  "Informe seu nível",
  "Pratique com seus tutores",
  "Acompanhe sua evolução",
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[var(--surface-soft)] text-text-primary">
      <header className="border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 md:px-8">
          <Logo />
          <nav className="flex items-center gap-2 sm:gap-3" aria-label="Acesso">
            <Link
              href="/login"
              className="rounded-xl px-3 py-2 text-sm font-semibold text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
            >
              Entrar
            </Link>
            <Link
              href="/register"
              className="inline-flex min-h-10 items-center rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white shadow-[0_3px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
            >
              Começar agora
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden border-b border-border bg-[var(--primary-deep)] text-white">
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            aria-hidden
            style={{
              background:
                "radial-gradient(circle at 20% 20%, rgba(37,99,235,.45), transparent 40%), radial-gradient(circle at 80% 0%, rgba(219,234,254,.25), transparent 35%)",
            }}
          />
          <div className="relative mx-auto grid max-w-6xl gap-10 px-5 py-16 md:px-8 md:py-24 lg:grid-cols-[1.2fr_.8fr] lg:items-center">
            <div>
              <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-semibold uppercase tracking-[.1em] text-white/70">
                <Flame className="size-4 fill-[var(--streak)] text-[var(--streak)]" aria-hidden />
                {BRAND.slogan}
              </p>
              <h1 className="max-w-2xl text-4xl font-bold leading-[1.08] tracking-[-.04em] md:text-5xl">
                Aprenda idiomas de forma prática, personalizada e divertida.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-white/75">
                Converse, pratique pronúncia, amplie seu vocabulário e acompanhe sua
                evolução com tutores de inteligência artificial — no seu ritmo, todos os dias.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/register"
                  className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-bold text-[var(--primary-strong)] shadow-[0_4px_0_rgba(15,42,95,.25)] hover:bg-primary-soft"
                >
                  Começar agora
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex min-h-12 items-center justify-center rounded-xl border-2 border-white/25 px-5 text-sm font-bold text-white hover:bg-white/10"
                >
                  Entrar
                </Link>
              </div>
              <p className="mt-8 text-sm text-white/45">{BRAND.institutional}</p>
            </div>
            <div className="hidden rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm lg:block" aria-hidden>
              <div className="space-y-3">
                {[
                  { label: "Conversação", status: "Em andamento", icon: MessagesSquare },
                  { label: "Pronúncia", status: "Disponível", icon: Volume2 },
                  { label: "Vocabulário", status: "Disponível", icon: BookOpen },
                  { label: "Revisão", status: "Disponível", icon: RotateCcw },
                ].map(({ label, status, icon: Icon }) => (
                  <div
                    key={label}
                    className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm"
                  >
                    <span className="flex items-center gap-2.5">
                      <Icon className="size-4 text-white/70" />
                      {label}
                    </span>
                    <span className="text-white/45">{status}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between rounded-xl border border-[var(--streak)]/30 bg-[var(--streak)]/10 px-4 py-3 text-sm">
                  <span className="flex items-center gap-2.5 font-semibold">
                    <Flame className="size-4 fill-[var(--streak)] text-[var(--streak)]" />
                    Sequência
                  </span>
                  <span className="font-bold text-[var(--streak)]">7 dias</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-16 md:px-8">
          <h2 className="text-2xl font-bold tracking-tight">Por que praticar no BeFluent</h2>
          <p className="mt-3 max-w-2xl text-text-secondary">
            Um ambiente claro para estudar com constância, sem poluição visual e com foco na fluência.
          </p>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {benefits.map((item) => {
              const colors = modeColorClasses[item.color];
              const Icon = item.icon;
              return (
                <article key={item.title} className="panel p-5">
                  <span className={`grid size-11 place-items-center rounded-xl ${colors.bg} ${colors.text}`}>
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <h3 className="mt-4 font-semibold">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-text-secondary">{item.description}</p>
                </article>
              );
            })}
          </div>
        </section>

        <section className="border-y border-border bg-surface">
          <div className="mx-auto max-w-6xl px-5 py-16 md:px-8">
            <h2 className="text-2xl font-bold tracking-tight">Idiomas disponíveis</h2>
            <p className="mt-3 text-text-secondary">
              Cinco idiomas com estratégias próprias de estudo.
            </p>
            <ul className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {LANGUAGES.map((lang) => (
                <li key={lang.code} className="rounded-2xl border border-border bg-[var(--surface-soft)] px-4 py-4 transition hover:border-primary">
                  <p className="font-semibold">{lang.namePt}</p>
                  <p className="mt-1 text-sm text-text-secondary">{lang.native}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-16 md:px-8">
          <h2 className="text-2xl font-bold tracking-tight">Como funciona</h2>
          <ol className="mt-8 grid gap-4 md:grid-cols-5">
            {steps.map((step, index) => (
              <li key={step} className="panel p-4">
                <span className="grid size-8 place-items-center rounded-full bg-primary-soft text-xs font-bold text-primary">
                  {index + 1}
                </span>
                <p className="mt-3 text-sm font-semibold leading-6">{step}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className="border-t border-border bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 md:flex-row md:items-end md:justify-between md:px-8">
          <div>
            <Logo />
            <p className="mt-3 text-sm text-text-secondary">{BRAND.slogan}</p>
            <p className="mt-2 text-sm text-text-secondary">{BRAND.poweredBy}</p>
          </div>
          <div className="flex gap-4 text-sm font-semibold">
            <Link href="/login" className="text-primary hover:underline">
              Entrar
            </Link>
            <Link href="/register" className="text-primary hover:underline">
              Criar conta
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
