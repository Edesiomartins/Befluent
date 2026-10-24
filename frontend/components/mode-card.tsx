import Link from "next/link";
import { ArrowUpRight, Clock } from "lucide-react";
import { type ModeMeta } from "@/lib/modes";

/**
 * Card de modo de aprendizado. Único componente para a grade completa
 * (`/learn`) e para "Prática livre" no dashboard — antes duplicado entre as
 * duas páginas com pequenas divergências de estilo.
 */
export function ModeCard({
  mode,
  recommended = false,
  compact = false,
  titleAs = "h3",
}: {
  mode: ModeMeta;
  recommended?: boolean;
  compact?: boolean;
  titleAs?: "h2" | "h3";
}) {
  const Icon = mode.icon;
  const Title = titleAs;

  return (
    <Link
      href={`/learn/${mode.slug}`}
      className={`group flex h-full items-start gap-3.5 rounded-2xl border bg-surface p-4.5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-all hover:-translate-y-0.5 hover:border-primary/45 hover:shadow-[0_6px_16px_-4px_rgba(15,23,42,0.06)] ${
        recommended
          ? "border-primary/50 bg-[linear-gradient(180deg,rgba(219,234,254,0.22)_0%,#ffffff_60%)]"
          : "border-border"
      }`}
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-primary/15 bg-primary-soft/75 text-primary transition-colors group-hover:bg-primary group-hover:text-white">
        <Icon className="size-4.5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <Title className="text-sm font-semibold tracking-[-0.01em] text-text-primary group-hover:text-primary">
              {mode.title}
            </Title>
            {recommended && (
              <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[0.7rem] font-semibold text-primary">
                Recomendado
              </span>
            )}
          </div>
          <ArrowUpRight
            className="size-4 shrink-0 text-text-secondary/60 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary"
            aria-hidden
          />
        </div>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-text-secondary">
          {mode.description}
        </p>
        {!compact && (
          <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-text-secondary tabular-nums">
            <Clock className="size-3.5" aria-hidden />
            {mode.duration}
          </p>
        )}
      </div>
    </Link>
  );
}
