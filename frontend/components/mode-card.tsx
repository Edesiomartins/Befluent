import Link from "next/link";
import { Clock } from "lucide-react";
import { modeColorClasses, type ModeMeta } from "@/lib/modes";

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
  const colors = modeColorClasses[mode.color];
  const Title = titleAs;

  return (
    <Link
      href={`/learn/${mode.slug}`}
      className={`group flex h-full items-start gap-3.5 rounded-xl border bg-surface p-4 transition-colors hover:border-primary/50 ${
        recommended ? "border-primary/60" : "border-border"
      }`}
    >
      <span
        className={`grid size-9 shrink-0 place-items-center rounded-lg bg-surface-soft ${colors.text}`}
      >
        <Icon className="size-[1.1rem]" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Title className="font-semibold group-hover:text-primary">{mode.title}</Title>
          {recommended && (
            <span className="text-xs font-semibold text-primary">Recomendado</span>
          )}
        </div>
        <p className="mt-0.5 line-clamp-2 text-sm leading-6 text-text-secondary">
          {mode.description}
        </p>
        {!compact && (
          <p className="mt-2 flex items-center gap-1 text-xs text-text-secondary">
            <Clock className="size-3.5" aria-hidden />
            {mode.duration}
          </p>
        )}
      </div>
    </Link>
  );
}
