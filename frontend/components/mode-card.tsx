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
      className={`panel group flex h-full items-start gap-3 p-4 transition hover:-translate-y-0.5 ${colors.ring} ${
        recommended ? "border-primary" : ""
      } ${compact ? "opacity-90 hover:opacity-100" : ""}`}
    >
      <span
        className={`grid ${compact ? "size-10" : "size-11"} shrink-0 place-items-center rounded-xl ${colors.bg} ${colors.text}`}
      >
        <Icon className="size-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <Title className="font-semibold group-hover:text-primary">{mode.title}</Title>
          {recommended && (
            <span className="rounded-full bg-primary-soft px-2 py-0.5 text-[.65rem] font-bold uppercase tracking-wide text-primary">
              Recomendado
            </span>
          )}
        </div>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-text-secondary">
          {mode.description}
        </p>
        {!compact && (
          <p className="mt-2 flex items-center gap-1 text-xs font-medium text-text-secondary">
            <Clock className="size-3.5" aria-hidden />
            {mode.duration}
          </p>
        )}
      </div>
    </Link>
  );
}
