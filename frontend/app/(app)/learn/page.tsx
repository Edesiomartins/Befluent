import Link from "next/link";
import { ArrowRight, Clock } from "lucide-react";
import { MODES, modeColorClasses } from "@/lib/modes";

export default function LearnPage() {
  const [guided, ...rest] = MODES;

  return (
    <div>
      <p className="text-sm font-semibold text-primary">Prática</p>
      <h1 className="mt-2 page-title">O que vamos praticar?</h1>
      <p className="mt-3 max-w-2xl leading-7 text-text-secondary">
        Escolha uma habilidade para trabalhar agora. Recomendações personalizadas aparecem após o onboarding.
      </p>

      <Link
        href={`/learn/${guided.slug}`}
        className="mt-8 grid gap-5 rounded-2xl bg-[var(--primary-deep)] p-6 text-white transition hover:brightness-110 sm:grid-cols-[1fr_auto] sm:items-center"
      >
        <div>
          <p className="text-xs font-semibold uppercase tracking-[.14em] text-white/60">Sugestão inicial</p>
          <h2 className="mt-2 text-xl font-semibold">{guided.title}</h2>
          <p className="mt-2 text-sm leading-6 text-white/70">
            Uma sequência estruturada para começar com clareza.
          </p>
        </div>
        <span className="inline-flex items-center gap-2 font-semibold">
          Começar <ArrowRight className="size-4" aria-hidden />
        </span>
      </Link>

      <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {rest.map((mode) => {
          const Icon = mode.icon;
          const colors = modeColorClasses[mode.color];
          return (
            <Link
              href={`/learn/${mode.slug}`}
              key={mode.slug}
              className={`panel group flex items-start gap-3 p-4 transition hover:-translate-y-0.5 ${colors.ring}`}
            >
              <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${colors.bg} ${colors.text}`}>
                <Icon className="size-5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="font-semibold group-hover:text-primary">{mode.title}</h2>
                <p className="mt-1 text-sm leading-6 text-text-secondary">{mode.description}</p>
                <p className="mt-2 flex items-center gap-1 text-xs font-medium text-text-secondary">
                  <Clock className="size-3.5" aria-hidden />
                  {mode.duration}
                </p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
