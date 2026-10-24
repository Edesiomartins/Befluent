import { Check, Circle } from "lucide-react";
import { EmptyState } from "@/components/ui";
import { LanguageProgressPanel } from "@/components/language-progress-panel";
import { DashboardLink, LevelBlock } from "@/components/dashboard/level-block";
import type { DashboardData } from "@/components/dashboard/types";
import { deriveDailyMission } from "@/lib/journey";
import type { TodayPayload } from "@/types/curriculum";

export function StudyDetails({
  data,
  today,
}: {
  data: DashboardData;
  today: TodayPayload | null;
}) {
  const language = data.active_language;
  const hasPlan = Boolean(language && data.onboarding_completed);
  const dayPlan = data.day_plan;
  const planItems = dayPlan?.items ?? [];
  const doneCount = planItems.filter((item) => item.done).length;
  const planPercent = planItems.length ? Math.round((doneCount / planItems.length) * 100) : 0;
  const mission = today?.day
    ? deriveDailyMission({
        day: today.day,
        weekTheme: today.week?.theme,
        languageName: language?.name_pt || "Seu idioma",
        level: today.week?.cefr_focus,
      })
    : null;

  return (
    <div className="grid gap-5">
      <header>
        <h1 className="page-title">Idioma e plano</h1>
        <p className="mt-2 text-sm text-text-secondary">
          O caminho de hoje continua na tela inicial.
        </p>
      </header>

      {data.language_progress && <LanguageProgressPanel progress={data.language_progress} />}

      <section className="panel p-6">
        <h2 className="label">Idioma ativo</h2>
        {hasPlan && language ? (
          <div className="mt-4 grid gap-4">
            <p className="text-lg font-semibold text-text-primary">
              {language.name_pt}
              <span className="ml-2 text-sm font-normal text-text-secondary">
                {language.native_name}
              </span>
            </p>
            <LevelBlock level={language.level} legacyLevel={language.level_estimate} />
            {language.goal && (
              <p className="text-sm text-text-secondary">Objetivo: {language.goal}</p>
            )}
            <DashboardLink href="/languages">Gerenciar idiomas</DashboardLink>
          </div>
        ) : (
          <EmptyState
            title="Escolha um idioma para começar."
            description="Defina o idioma principal no onboarding."
            action={<DashboardLink href="/onboarding">Configurar plano</DashboardLink>}
          />
        )}
      </section>

      <section className="panel p-6">
        <h2 className="label">Plano do dia</h2>
        {hasPlan ? (
          <div className="mt-4 grid gap-5">
            {dayPlan?.minutes_per_day != null && (
              <div>
                <div className="flex items-baseline justify-between gap-3">
                  <p>
                    <span className="display-number text-3xl leading-none">
                      {dayPlan.minutes_per_day}
                    </span>
                    <span className="ml-1.5 text-sm text-text-secondary">min por dia</span>
                  </p>
                  <span className="text-sm font-semibold tabular-nums">{planPercent}%</span>
                </div>
                <div
                  className="mt-3 h-1.5 rounded-full bg-surface-elevated"
                  role="progressbar"
                  aria-label="Progresso do plano do dia"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={planPercent}
                  aria-valuetext={`${doneCount} de ${planItems.length} itens concluídos`}
                >
                  <div className="h-full rounded-full bg-primary" style={{ width: `${planPercent}%` }} />
                </div>
              </div>
            )}
            {!today && (
              <ul className="grid gap-2.5">
                {planItems.map((item) => (
                  <li
                    key={item.label}
                    className={`flex items-start gap-2.5 text-sm leading-5 ${item.done ? "text-text-secondary" : "text-text-primary"}`}
                  >
                    {item.done ? (
                      <Check className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
                    ) : (
                      <Circle className="mt-0.5 size-4 shrink-0 text-border" aria-hidden />
                    )}
                    {item.label}
                  </li>
                ))}
              </ul>
            )}
            {today && dayPlan?.goal && (
              <p className="text-sm text-text-secondary">
                Objetivo: <span className="font-medium text-text-primary">{dayPlan.goal}</span>
              </p>
            )}
          </div>
        ) : (
          <EmptyState
            title="Plano ainda não definido."
            description="Conclua o onboarding para montar o plano do dia."
            action={<DashboardLink href="/onboarding">Configurar plano</DashboardLink>}
          />
        )}
      </section>

      {mission && (
        <section aria-labelledby="mission-phases">
          <h2 id="mission-phases" className="section-title">Etapas da missão</h2>
          <ol className="mt-4 flex flex-wrap gap-2" aria-label="Progresso da missão">
            {mission.phases.map((phase) => (
              <li
                key={phase.key}
                className="inline-flex min-h-9 items-center gap-2 rounded-full border border-border px-3 text-xs font-semibold"
                aria-current={phase.state === "current" ? "step" : undefined}
              >
                <span aria-hidden>
                  {phase.state === "done" ? "✓" : phase.state === "current" ? "●" : "○"}
                </span>
                {phase.label}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
