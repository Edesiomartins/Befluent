import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";
import { LEVEL_SOURCE_LABELS, levelShortCode } from "@/lib/levels";
import type { DashboardLevel } from "@/types/placement";

export function DashboardLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-colors hover:text-[var(--primary-hover)] hover:underline"
    >
      <span>{children}</span>
      <ArrowUpRight className="size-3.5" aria-hidden />
    </Link>
  );
}

/** Nível do idioma ativo. Nunca inventa nível: pendente vira convite ao teste. */
export function LevelBlock({
  level,
  legacyLevel,
}: {
  level?: DashboardLevel;
  legacyLevel: string | null;
}) {
  if (level?.assessment_status === "partial" && !level.current_level) {
    return (
      <div className="rounded-xl border border-border bg-[var(--surface-soft)] p-4">
        <p className="text-sm font-semibold">Perfil parcial de competências</p>
        <p className="mt-1 text-sm text-text-secondary">
          Seu teste foi concluído. Ainda falta cobertura para um nível global; você já pode praticar.
        </p>
        <div className="mt-3 flex gap-4">
          <DashboardLink href={`/placement-test/${level.last_assessment_id}/resultado`}>
            Ver perfil
          </DashboardLink>
          <DashboardLink href="/learn">Praticar habilidades</DashboardLink>
        </div>
      </div>
    );
  }
  if (!level || level.needs_placement_test || !level.current_level) {
    return (
      <div className="rounded-xl border border-border bg-[var(--surface-soft)] p-4">
        <p className="text-sm font-semibold">Nível ainda não definido</p>
        <p className="mt-1 text-sm text-text-secondary">
          {legacyLevel
            ? "Faça o teste para uma estimativa por competência."
            : "Descubra seu nível em cerca de 15 minutos."}
        </p>
        <div className="mt-3">
          <DashboardLink href="/placement-test">Fazer teste de nível</DashboardLink>
        </div>
      </div>
    );
  }

  const assessed = level.skills.filter((skill) => skill.estimated_level);

  return (
    <div className="rounded-xl border border-border bg-[var(--surface-soft)] p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="display-number text-3xl leading-none text-text-primary">
          {levelShortCode(level.current_level)}
        </span>
        <span className="tech-badge">
          {LEVEL_SOURCE_LABELS[level.source]}
        </span>
      </div>
      {level.details && (
        <p className="mt-2 text-sm font-medium text-text-secondary">{level.details.name_pt}</p>
      )}
      {level.from_test && (
        <p className="mt-1 text-xs text-text-secondary">
          Avaliado em{" "}
          {level.assessed_at
            ? new Date(level.assessed_at).toLocaleDateString("pt-BR")
            : "—"}
          {level.confidence_label ? `, confiança ${level.confidence_label}` : ""}
        </p>
      )}
      {assessed.length > 0 && (
        <ul className="mt-4 grid gap-2 border-t border-border pt-3 text-sm">
          {assessed.map((skill) => (
            <li key={skill.skill} className="flex items-center justify-between gap-3">
              <span className="text-text-secondary">{skill.label}</span>
              <span className="rounded-md bg-surface px-2 py-0.5 text-xs font-semibold tabular-nums text-text-primary shadow-[0_1px_2px_rgba(15,23,42,0.03)]">
                {levelShortCode(skill.estimated_level)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1">
        {level.placement_test_id && (
          <DashboardLink href={`/placement-test/${level.placement_test_id}/resultado`}>
            Ver resultado completo
          </DashboardLink>
        )}
        {!level.from_test && (
          <DashboardLink href="/placement-test">Confirmar com o teste</DashboardLink>
        )}
      </div>
    </div>
  );
}
