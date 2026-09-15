"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { ArrowRight, Check, Circle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { DashboardSkeleton } from "@/components/dashboard-skeleton";
import { EmptyState } from "@/components/ui";
import { ModeCard } from "@/components/mode-card";
import { getMode } from "@/lib/modes";
import { LEVEL_SOURCE_LABELS, levelShortCode } from "@/lib/levels";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useTodayInCurriculum } from "@/hooks/use-curriculum";
import type { DashboardLevel } from "@/types/placement";
import type { TodayPayload } from "@/types/curriculum";

type DashboardData = {
  onboarding_completed: boolean;
  active_language: {
    code: string;
    name_pt: string;
    native_name: string;
    level_estimate: string | null;
    goal: string | null;
    minutes_per_day: number | null;
    skills: string[];
    onboarding_completed: boolean;
    user_language_id: string;
    level?: DashboardLevel;
  } | null;
  next_activity: {
    title: string;
    description: string;
    href: string;
    cta: string;
    kind: string;
  };
  day_plan: {
    minutes_per_day: number | null;
    goal: string | null;
    skills: string[];
    items: Array<{ label: string; done: boolean }>;
  };
  progress: {
    vocabulary_items: number;
    study_sessions: number;
    reviews_due_count: number;
    streak_days: number;
    total_minutes?: number;
    minutes_today?: number;
    total_minutes_label?: string;
  };
  reviews_due_count: number;
  reviews_due: Array<{
    id: string;
    item_type: string;
    reference_id: string;
    payload: Record<string, unknown>;
    next_review_at: string | null;
  }>;
  recent_activity: Array<{
    id: string;
    status: string;
    summary: string | null;
    started_at: string | null;
    ended_at: string | null;
    minutes?: number;
  }>;
};

// "voice" é o card "Conversação" do hub (ver lib/modes.ts) — o slug antigo
// "conversation" (diálogo só por texto) não é mais exibido como atalho aqui.
const practiceSlugs = ["voice", "vocabulary", "review", "guided", "listening", "writing"];

function LinkAction({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-sm font-semibold text-primary hover:underline">
      {children}
    </Link>
  );
}

/** Nível do idioma ativo. Nunca inventa nível: pendente vira convite ao teste. */
function LevelBlock({
  level,
  legacyLevel,
}: {
  level?: DashboardLevel;
  legacyLevel: string | null;
}) {
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
          <LinkAction href="/placement-test">Fazer teste de nível</LinkAction>
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
          <LinkAction href={`/placement-test/${level.placement_test_id}/resultado`}>
            Ver resultado completo
          </LinkAction>
        )}
        {!level.from_test && (
          <LinkAction href="/placement-test">Confirmar com o teste</LinkAction>
        )}
      </div>
    </div>
  );
}

/** Dia corrente do cronograma — o bloco principal do painel.
 *
 *  Os blocos são uma sequência real (Ativar → … → Consolidar), por isso aparecem
 *  numerados. Sem cronograma ativo, o painel mostra a próxima atividade no lugar.
 */
function TodayInCurriculum({ today }: { today: TodayPayload }) {
  const { day, week, curriculum } = today;
  if (!day) return null;
  const late = curriculum.progress.overdue_days;

  return (
    <section className="rounded-2xl bg-[var(--primary-deep)] p-6 text-white sm:p-8">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm text-white/65">
        <p>Hoje no seu cronograma</p>
        <p className="tabular-nums">
          Dia {day.day_number} de {curriculum.progress.days_total} · {day.total_minutes} min
        </p>
      </div>

      <h2 className="page-title mt-3 text-white">
        {week ? week.theme : `Dia ${day.day_number}`}
      </h2>
      {week?.is_checkpoint && (
        <p className="mt-2 text-sm text-[var(--gold)]">Semana de checkpoint</p>
      )}

      <ol className="mt-7 grid gap-px overflow-hidden rounded-xl bg-white/10 sm:grid-cols-5">
        {day.blocks.map((block, index) => {
          const done = block.status === "completed";
          const current = Boolean(block.is_current);
          return (
            <li
              key={block.id}
              className={`flex items-center gap-3 px-4 py-3 sm:block sm:px-3 sm:py-4 ${
                current ? "bg-white text-[var(--primary-deep)]" : "bg-[var(--primary-deep)]"
              }`}
              aria-current={current ? "step" : undefined}
            >
              <span
                className={`display-number grid size-7 shrink-0 place-items-center rounded-full text-sm sm:mb-3 ${
                  done
                    ? "bg-white/15 text-white"
                    : current
                      ? "bg-primary text-white"
                      : "border border-white/25 text-white/70"
                }`}
              >
                {done ? <Check className="size-3.5" aria-label="Concluído" /> : index + 1}
              </span>
              <span className="min-w-0">
                <span className={`block text-sm font-semibold leading-5 ${done ? "text-white/55" : ""}`}>
                  {block.skill_label}
                </span>
                {block.phase_label && (
                  <span className={`block text-xs ${current ? "text-text-secondary" : "text-white/50"}`}>
                    {block.phase_label}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ol>

      <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Link
          href={`/cronograma/dia/${day.id}`}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-[var(--primary-deep)] hover:bg-white/90"
        >
          {day.blocks_completed > 0 ? "Continuar o dia" : "Começar o dia"}
          <ArrowRight className="size-4" aria-hidden />
        </Link>
        {late > 0 && (
          <Link
            href="/cronograma"
            className="text-sm text-white/65 underline-offset-4 hover:text-white hover:underline"
          >
            {late} {late === 1 ? "jornada" : "jornadas"} atrás do ritmo recomendado
          </Link>
        )}
      </div>
    </section>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const { code, resolved } = useActiveLanguage();
  const todayResource = useTodayInCurriculum(resolved ? code : null);

  useEffect(() => {
    let active = true;
    api<DashboardData>("/api/v1/dashboard")
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar o painel.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) return <DashboardSkeleton />;

  if (error) {
    return (
      <div>
        <h1 className="page-title">Bem-vindo ao BeFluent</h1>
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}
        </p>
      </div>
    );
  }

  const language = data?.active_language ?? null;
  const hasPlan = Boolean(language && data?.onboarding_completed);
  const next = data?.next_activity;
  const dayPlan = data?.day_plan;
  const progress = data?.progress;
  const reviews = data?.reviews_due ?? [];
  const activity = data?.recent_activity ?? [];
  // Silencioso sem cronograma ativo: o convite para criar um está em /cronograma.
  const today =
    todayResource.status === "ready" && todayResource.data?.day ? todayResource.data : null;

  const planItems = dayPlan?.items ?? [];
  const doneCount = planItems.filter((item) => item.done).length;
  const planPercent = planItems.length ? Math.round((doneCount / planItems.length) * 100) : 0;

  const stats = [
    { value: progress?.streak_days ?? 0, label: "dias seguidos" },
    { value: progress?.vocabulary_items ?? 0, label: "palavras" },
    { value: progress?.study_sessions ?? 0, label: "sessões" },
    { value: progress?.reviews_due_count ?? 0, label: "revisões" },
  ];

  return (
    <div>
      <header className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
        <div>
          <h1 className="page-title">{hasPlan ? "Seu estudo de hoje" : "Bem-vindo ao BeFluent"}</h1>
          {!hasPlan && (
            <p className="mt-2 text-text-secondary">
              Configure seu plano para liberar o caminho diário.
            </p>
          )}
        </div>
        <dl className="grid grid-cols-4 divide-x divide-border">
          {stats.map((stat) => (
            <div key={stat.label} className="flex flex-col-reverse px-4 first:pl-0 last:pr-0 md:px-5">
              <dt className="mt-1.5 text-xs text-text-secondary">{stat.label}</dt>
              <dd className="display-number text-2xl leading-none md:text-[1.75rem]">{stat.value}</dd>
            </div>
          ))}
        </dl>
      </header>

      <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1.75fr)_minmax(0,1fr)]">
        {today ? (
          <TodayInCurriculum today={today} />
        ) : (
          <article className="rounded-2xl bg-[var(--primary-deep)] p-6 text-white sm:p-8">
            <p className="text-sm text-white/65">Próxima atividade</p>
            <h2 className="page-title mt-3 text-white">{next?.title}</h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-white/70">{next?.description}</p>
            {next && (
              <Link
                href={next.href}
                className="mt-7 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-[var(--primary-deep)] hover:bg-white/90"
              >
                {next.cta}
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            )}
          </article>
        )}

        <article className="panel p-6">
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
                  <div className="mt-3 h-1.5 rounded-full bg-surface-elevated">
                    <div
                      className="h-full rounded-full bg-primary transition-[width]"
                      style={{ width: `${planPercent}%` }}
                    />
                  </div>
                </div>
              )}
              {/* Com cronograma ativo os itens repetem os blocos já mostrados ao lado. */}
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
              action={<LinkAction href="/onboarding">Configurar plano</LinkAction>}
            />
          )}
        </article>
      </div>

      <section className="panel mt-5 grid md:grid-cols-2 md:divide-x md:divide-border">
        <article className="p-6">
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
              <LinkAction href="/languages">Gerenciar idiomas</LinkAction>
            </div>
          ) : (
            <EmptyState
              title="Escolha um idioma para começar."
              description="Defina o idioma principal no onboarding."
              action={<LinkAction href="/onboarding">Configurar plano</LinkAction>}
            />
          )}
        </article>

        <article className="border-t border-border p-6 md:border-t-0">
          <h2 className="label">Revisões</h2>
          {reviews.length > 0 ? (
            <div className="mt-4 grid gap-3">
              <p className="text-sm text-text-secondary">
                {reviews.length}{" "}
                {reviews.length === 1 ? "revisão pendente" : "revisões pendentes"}.
              </p>
              <ul className="grid gap-2">
                {reviews.slice(0, 3).map((item) => (
                  <li key={item.id} className="text-sm text-text-primary">
                    {item.item_type}
                    {typeof item.payload?.term === "string" ? `: ${item.payload.term}` : ""}
                  </li>
                ))}
              </ul>
              <LinkAction href="/learn/review">Abrir revisões</LinkAction>
            </div>
          ) : (
            <EmptyState
              title="Nenhuma revisão pendente por enquanto."
              description="Itens aparecem aqui quando houver revisão agendada."
              action={<LinkAction href="/learn/review">Abrir revisões</LinkAction>}
            />
          )}
        </article>
      </section>

      <section className="mt-10">
        <div className="flex items-baseline justify-between gap-4">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <h2 className="section-title">Prática livre</h2>
            <p className="text-sm text-text-secondary">Fora da sequência do dia</p>
          </div>
          <LinkAction href="/learn">Ver todas</LinkAction>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {practiceSlugs.map((slug) => {
            const mode = getMode(slug);
            if (!mode) return null;
            return <ModeCard key={slug} mode={mode} compact />;
          })}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="section-title">Atividade recente</h2>
        {activity.length > 0 ? (
          <ul className="mt-3 divide-y divide-border border-y border-border">
            {activity.map((session) => (
              <li
                key={session.id}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3 text-sm"
              >
                <span className="font-medium text-text-primary">
                  {session.summary ||
                    (session.status === "completed" ? "Sessão concluída" : "Sessão de estudo")}
                </span>
                <span className="text-text-secondary tabular-nums">
                  {session.started_at
                    ? new Date(session.started_at).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "short",
                      })
                    : null}
                  {typeof session.minutes === "number" ? ` · ${session.minutes} min` : null}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title="Você ainda não iniciou nenhuma prática."
            description="Abra o caminho do dia no cronograma para começar."
            action={
              <LinkAction href={next?.kind === "curriculum" ? next.href : "/cronograma"}>
                Abrir caminho
              </LinkAction>
            }
          />
        )}
      </section>
    </div>
  );
}
