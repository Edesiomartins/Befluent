import Link from "next/link";
import {
  BookOpen,
  Headphones,
  MessagesSquare,
  RotateCcw,
  TrendingUp,
  Volume2,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { BRAND, LANGUAGES } from "@/lib/brand";

const practices = [
  {
    title: "Conversação",
    description: "Diálogos no seu nível, com correções no momento certo.",
    icon: MessagesSquare,
  },
  {
    title: "Pronúncia",
    description: "Treine a fala e receba orientações objetivas.",
    icon: Volume2,
  },
  {
    title: "Vocabulário",
    description: "Aprenda palavras no contexto em que elas aparecem.",
    icon: BookOpen,
  },
  {
    title: "Audição",
    description: "Escute, entenda e fortaleça a compreensão oral.",
    icon: Headphones,
  },
  {
    title: "Revisão",
    description: "Retome o que importa no ritmo certo para lembrar.",
    icon: RotateCcw,
  },
  {
    title: "Progresso",
    description: "Veja o que avançou e o que praticar a seguir.",
    icon: TrendingUp,
  },
];

const steps = [
  {
    title: "Crie sua conta",
    description: "Comece em poucos minutos, sem configuração complicada.",
  },
  {
    title: "Escolha o idioma",
    description: "Inglês, espanhol da Espanha, francês, japonês ou mandarim.",
  },
  {
    title: "Defina seu ponto de partida",
    description: "Informe nível, objetivo e quanto tempo quer estudar por dia.",
  },
  {
    title: "Pratique com foco",
    description: "Converse, revise e evolua com tutores de IA no seu ritmo.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[var(--surface-soft)] text-text-primary">
      <header className="sticky top-0 z-20 border-b border-border/80 bg-surface/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 md:px-8">
          <Logo />
          <nav className="flex items-center gap-2 sm:gap-3" aria-label="Acesso">
            <Link
              href="/login"
              className="rounded-xl px-3 py-2 text-sm font-semibold text-text-secondary transition hover:bg-surface-elevated hover:text-text-primary"
            >
              Entrar
            </Link>
            <Link
              href="/register"
              className="inline-flex min-h-10 items-center rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white shadow-[0_3px_0_var(--primary-shadow)] transition hover:bg-[var(--primary-hover)]"
            >
              Começar agora
            </Link>
          </nav>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden bg-[var(--primary-deep)] text-white">
          <div
            className="pointer-events-none absolute inset-0"
            aria-hidden
            style={{
              background:
                "radial-gradient(ellipse 70% 60% at 15% 20%, rgba(37,99,235,.55), transparent 55%), radial-gradient(ellipse 50% 45% at 90% 10%, rgba(219,234,254,.22), transparent 50%), linear-gradient(180deg, transparent 70%, rgba(11,31,68,.35))",
            }}
          />
          <div className="relative mx-auto grid min-h-[min(78vh,720px)] max-w-6xl items-end gap-12 px-5 pb-16 pt-20 md:px-8 md:pb-20 md:pt-28 lg:grid-cols-[1.15fr_.85fr] lg:items-center">
            <div className="landing-fade-up">
              <p className="text-sm font-semibold tracking-[0.18em] text-white/55 uppercase">
                {BRAND.name}
              </p>
              <h1 className="mt-4 max-w-2xl text-[clamp(2.4rem,6vw,3.75rem)] font-bold leading-[1.05] tracking-[-0.045em]">
                Aprenda. Pratique. Fale.
              </h1>
              <p className="mt-6 max-w-lg text-lg leading-8 text-white/72">
                Um espaço calmo para estudar idiomas com inteligência artificial —
                conversação, pronúncia, vocabulário e revisão no seu ritmo.
              </p>
              <p className="mt-10 text-sm text-white/40">{BRAND.institutional}</p>
            </div>

            <aside
              className="landing-fade-up landing-fade-up-delay hidden border-l border-white/15 pl-8 lg:block"
              aria-hidden
            >
              <p className="text-xs font-semibold tracking-[0.14em] text-white/45 uppercase">
                Sua prática
              </p>
              <ul className="mt-6 space-y-5">
                {[
                  ["Conversação", "Em andamento"],
                  ["Pronúncia", "Disponível"],
                  ["Vocabulário", "Disponível"],
                  ["Revisão", "Disponível"],
                ].map(([label, status]) => (
                  <li key={label} className="flex items-baseline justify-between gap-6">
                    <span className="text-base font-medium text-white/90">{label}</span>
                    <span className="text-sm text-white/40">{status}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-8 border-t border-white/15 pt-5">
                <p className="text-sm text-white/55">
                  Constância diária, progresso visível.
                </p>
              </div>
            </aside>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-20 md:px-8">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight md:text-[2rem]">
              Pratique o que realmente importa
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-secondary">
              Menos distração, mais fluência. Cada atividade tem um objetivo claro.
            </p>
          </div>
          <div className="mt-12 grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
            {practices.map(({ title, description, icon: Icon }) => (
              <article key={title} className="border-t border-border pt-5">
                <Icon className="size-5 text-primary" aria-hidden />
                <h3 className="mt-4 text-base font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-text-secondary">{description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="border-y border-border bg-surface">
          <div className="mx-auto max-w-6xl px-5 py-20 md:px-8">
            <div className="max-w-2xl">
              <h2 className="text-3xl font-bold tracking-tight md:text-[2rem]">
                Cinco idiomas, cada um no seu caminho
              </h2>
              <p className="mt-4 text-lg leading-8 text-text-secondary">
                Estratégias próprias para inglês, espanhol da Espanha, francês, japonês e mandarim.
              </p>
            </div>
            <ul className="mt-12 divide-y divide-border border-y border-border">
              {LANGUAGES.map((lang) => (
                <li
                  key={lang.code}
                  className="flex flex-col gap-1 py-5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-8"
                >
                  <span className="text-lg font-semibold tracking-tight">{lang.namePt}</span>
                  <span className="text-sm text-text-secondary">{lang.native}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-5 py-20 md:px-8">
          <div className="max-w-2xl">
            <h2 className="text-3xl font-bold tracking-tight md:text-[2rem]">
              Como começar
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-secondary">
              Um caminho simples do primeiro acesso até a prática diária.
            </p>
          </div>
          <ol className="mt-12 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {steps.map((step, index) => (
              <li key={step.title} className="relative">
                <span className="text-sm font-bold tracking-[0.12em] text-primary">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3 className="mt-3 text-base font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-text-secondary">{step.description}</p>
              </li>
            ))}
          </ol>
        </section>

        <section className="border-t border-border bg-[var(--primary-deep)] text-white">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-16 md:flex-row md:items-end md:justify-between md:px-8 md:py-20">
            <div className="max-w-xl">
              <h2 className="text-3xl font-bold tracking-tight md:text-[2rem]">
                Constância gera fluência.
              </h2>
              <p className="mt-4 text-base leading-7 text-white/65">
                Comece pelo topo da página quando quiser criar sua conta ou entrar.
              </p>
            </div>
            <p className="text-sm text-white/40">{BRAND.poweredBy}</p>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-5 py-10 md:flex-row md:items-end md:justify-between md:px-8">
          <div>
            <Logo />
            <p className="mt-3 max-w-sm text-sm leading-6 text-text-secondary">
              {BRAND.description}
            </p>
          </div>
          <div className="flex gap-5 text-sm font-semibold">
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
