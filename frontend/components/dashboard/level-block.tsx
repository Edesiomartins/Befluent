import Link from "next/link";
import type { ReactNode } from "react";
import { LEVEL_SOURCE_LABELS, levelShortCode } from "@/lib/levels";
import type { DashboardLevel } from "@/types/placement";

export function DashboardLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-sm font-semibold text-primary hover:underline">
      {children}
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
      <div>
        <p className="text-sm font-semibold">Perfil parcial de competências</p>
        <p className="mt-1 text-sm text-text-secondary">
          Seu teste foi concluído. Ainda falta cobertura para um nível global; você já pode praticar.
        </p>
        <div className="mt-2 flex gap-4">
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
      <div>
        <p className="text-sm font-semibold">Nível ainda não definido</p>
        <p className="mt-1 text-sm text-text-secondary">
          {legacyLevel
            ? "Faça o teste para uma estimativa por competência."
            : "Descubra seu nível em cerca de 15 minutos."}
        </p>
        <div className="mt-2">
          <DashboardLink href="/placement-test">Fazer teste de nível</DashboardLink>
        </div>
      </div>
    );
  }

  const assessed = level.skills.filter((skill) => skill.estimated_level);

  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="display-number text-3xl leading-none">
          {levelShortCode(level.current_level)}
        </span>
        <span className="text-sm text-text-secondary">
          {LEVEL_SOURCE_LABELS[level.source]}
        </span>
      </div>
      {level.details && (
        <p className="mt-1.5 text-sm text-text-secondary">{level.details.name_pt}</p>
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
        <ul className="mt-4 grid gap-1.5 text-sm">
          {assessed.map((skill) => (
            <li key={skill.skill} className="flex justify-between gap-3">
              <span className="text-text-secondary">{skill.label}</span>
              <span className="font-medium tabular-nums">{levelShortCode(skill.estimated_level)}</span>
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
