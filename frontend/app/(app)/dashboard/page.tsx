"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  Circle,
  Flame,
  Sparkles,
  Trophy,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { DashboardSkeleton } from "@/components/dashboard-skeleton";
import { EmptyState } from "@/components/ui";
import { ModeCard } from "@/components/mode-card";
import { getMode } from "@/lib/modes";
import { LEVEL_SOURCE_LABELS, levelShortCode } from "@/lib/levels";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useTodayInCurriculum } from "@/hooks/use-curriculum";
import type { DashboardLevel } from "@/types/placement";

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
      <div className="rounded-xl border border-primary/25 bg-primary-soft/40 p-4">
        <p className="text-sm font-semibold">Nível ainda não definido</p>
        <p className="mt-1 text-sm text-text-secondary">
          {legacyLevel
            ? "Faça o teste para uma estimativa por competência."
            : "Descubra seu nível em cerca de 15 minutos."}
        </p>
        <Link
          href="/placement-test"
          className="mt-3 inline-flex text-sm font-semibold text-primary hover:underline"
        >
          Fazer teste de nível
        </Link>
      </div>
    );
  }

  const assessed = level.skills.filter((skill) => skill.estimated_level);

  return (
    <div>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-2xl font-bold tracking-tight text-primary">
          {levelShortCode(level.current_level)}
        </span>
        <span className="text-sm text-text-secondary">
          {LEVEL_SOURCE_LABELS[level.source]}
        </span>
      </div>
      {level.details && (
        <p className="mt-1 text-sm text-text-secondary">{level.details.name_pt}</p>
      )}

      {level.from_test && (
        <p className="mt-2 text-xs text-text-secondary">
          Avaliado em{" "}
          {level.assessed_at
            ? new Date(level.assessed_at).toLocaleDateString("pt-BR")
            : "—"}
          {level.confidence_label ? ` · confiança ${level.confidence_label}` : ""}
        </p>
      )}

      {assessed.length > 0 && (
        <ul className="mt-3 grid gap-1 text-sm">
          {assessed.map((skill) => (
            <li key={skill.skill} className="flex justify-between gap-3">
              <span className="text-text-secondary">{skill.label}</span>
              <span className="font-medium">{levelShortCode(skill.estimated_level)}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {level.placement_test_id && (
          <Link
            href={`/placement-test/${level.placement_test_id}/resultado`}
            className="text-sm font-semibold text-primary hover:underline"
          >
            Ver resultado completo
          </Link>
        )}
        {!level.from_test && (
          <Link
            href="/placement-test"
            className="text-sm font-semibold text-primary hover:underline"
          >
            Confirmar com o teste
          </Link>
        )}
      </div>
    </div>
  );
}

/** Card do dia corrente do cronograma.
 *
 *  Fica em silêncio quando não há cronograma ativo: quem ainda não gerou um não
 *  precisa ver um erro no painel — o convite para criar está em /cronograma.
 */
function TodayInCurriculum() {
  const { code, resolved } = useActiveLanguage();
  const { status, data } = useTodayInCurriculum(resolved ? code : null);

  if (status !== "ready" || !data.day) return null;

  const { day, week, curriculum } = data;
  const remaining = day.blocks_total - day.blocks_completed;
  const late = curriculum.progress.overdue_days;

  return (
    <section className="panel mt-5 p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Hoje no seu cronograma
        </p>
        <span className="text-sm text-text-secondary">
          Dia {day.day_number} de {curriculum.progress.days_total}
        </span>
      </div>

      <h2 className="mt-3 text-lg font-semibold">
        {week ? week.theme : `Dia ${day.day_number}`}
        {week?.is_checkpoint && (
          <span className="ml-2 rounded-md bg-[var(--gold-soft)] px-2 py-0.5 text-xs font-semibold text-[var(--gold-ink)]">
            Checkpoint
          </span>
        )}
      </h2>
      <p className="mt-1 text-sm text-text-secondary">
        {remaining} {remaining === 1 ? "bloco restante" : "blocos restantes"} ·{" "}
        {day.total_minutes} min estimados
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        {day.blocks.map((block) => (
          <span
            key={block.id}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              block.status === "completed"
                ? "bg-[var(--success-soft)] text-success line-through"
                : "bg-surface-elevated"
            }`}
          >
            {block.skill_label}
          </span>
        ))}
      </div>

      {late > 0 && (
        <p className="mt-4 text-sm text-warning">
          {late} {late === 1 ? "dia atrasado" : "dias atrasados"}.{" "}
          <Link href="/cronograma" className="font-semibold underline">
            Ver opções de reagendamento
          </Link>
        </p>
      )}

      <Link
        href={`/cronograma/dia/${day.id}`}
        className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
      >
        {day.blocks_completed > 0 ? "Continuar o dia" : "Começar o dia"}
        <ArrowRight className="size-4" aria-hidden />
      </Link>
    </section>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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

  const planItems = dayPlan?.items ?? [];
  const doneCount = planItems.filter((item) => item.done).length;
  const planPercent = planItems.length ? Math.round((doneCount / planItems.length) * 100) : 0;

  return (
    <div>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-sm font-semibold text-primary">Painel</p>
          <h1 className="page-title">Bem-vindo ao BeFluent</h1>
          <p className="mt-3 text-text-secondary">
            {hasPlan
              ? "Continue o caminho do dia — a sequência é o foco do BeFluent."
              : "Configure seu plano para desbloquear o caminho diário."}
          </p>
        </div>
      </div>

      {/* Estatísticas */}
      <section className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="panel flex items-center gap-3 p-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-[var(--streak-soft)] text-[var(--streak-shadow)]">
            <Flame className="size-6 fill-current" aria-hidden />
          </span>
          <div>
            <p className="text-xl font-extrabold leading-tight tracking-tight">{progress?.streak_days ?? 0}</p>
            <p className="text-xs text-text-secondary">dia(s) seguidos</p>
          </div>
        </div>
        <div className="panel flex items-center gap-3 p-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-[var(--violet-soft)] text-[var(--violet)]">
            <BookOpen className="size-6" aria-hidden />
          </span>
          <div>
            <p className="text-xl font-extrabold leading-tight tracking-tight">{progress?.vocabulary_items ?? 0}</p>
            <p className="text-xs text-text-secondary">palavras</p>
          </div>
        </div>
        <div className="panel flex items-center gap-3 p-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-[var(--gold-soft)] text-[var(--gold-ink)]">
            <Trophy className="size-6" aria-hidden />
          </span>
          <div>
            <p className="text-xl font-extrabold leading-tight tracking-tight">{progress?.study_sessions ?? 0}</p>
            <p className="text-xs text-text-secondary">sessões</p>
          </div>
        </div>
        <div className="panel flex items-center gap-3 p-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-[var(--success-soft)] text-success">
            <Sparkles className="size-6" aria-hidden />
          </span>
          <div>
            <p className="text-xl font-extrabold leading-tight tracking-tight">{progress?.reviews_due_count ?? 0}</p>
            <p className="text-xs text-text-secondary">revisões</p>
          </div>
        </div>
      </section>

      <TodayInCurriculum />

      {/* Próxima atividade | Plano do dia */}
      <section className="mt-5 grid gap-5 lg:grid-cols-2">
        <article className="relative overflow-hidden rounded-2xl bg-[var(--primary-deep)] p-6 text-white">
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            aria-hidden
            style={{
              background:
                "radial-gradient(circle at 85% 0%, rgba(37,99,235,.6), transparent 45%)",
            }}
          />
          <p className="relative text-xs font-semibold uppercase tracking-[.14em] text-white/60">
            Próxima atividade
          </p>
          <h2 className="relative mt-3 text-2xl font-semibold tracking-tight">{next?.title}</h2>
          <p className="relative mt-2 text-sm leading-6 text-white/70">{next?.description}</p>
          {next && (
            <Link
              href={next.href}
              className="relative mt-6 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-[var(--primary-deep)] hover:bg-white/90"
            >
              {next.cta}
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          )}
        </article>

        <article className="panel p-6">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Plano do dia
          </p>
          {hasPlan ? (
            <div className="mt-4 grid gap-4">
              {dayPlan?.minutes_per_day != null && (
                <div>
                  <div className="flex items-center justify-between text-sm text-text-secondary">
                    <span>
                      Meta: <span className="font-semibold text-text-primary">{dayPlan.minutes_per_day} min</span>
                    </span>
                    <span className="font-semibold text-success">{planPercent}%</span>
                  </div>
                  <div className="mt-2 h-2.5 rounded-full bg-surface-elevated">
                    <div
                      className="h-full rounded-full bg-success transition-[width]"
                      style={{ width: `${planPercent}%` }}
                    />
                  </div>
                </div>
              )}
              <ul className="grid gap-2.5">
                {planItems.map((item) => (
                  <li
                    key={item.label}
                    className={`flex items-center gap-2.5 text-sm ${item.done ? "text-text-secondary line-through" : "text-text-primary"}`}
                  >
                    {item.done ? (
                      <Check className="size-4 shrink-0 text-success" aria-hidden />
                    ) : (
                      <Circle className="size-4 shrink-0 text-border" aria-hidden />
                    )}
                    {item.label}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <EmptyState
              title="Plano ainda não definido."
              description="Conclua o onboarding para montar o plano do dia."
              action={
                <Link href="/onboarding" className="text-sm font-semibold text-primary hover:underline">
                  Configurar plano
                </Link>
              }
            />
          )}
        </article>
      </section>

      {/* Idioma ativo | Revisões */}
      <section className="mt-5 grid gap-5 md:grid-cols-2">
        <article className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Idioma ativo
          </p>
          {hasPlan && language ? (
            <div className="mt-4 grid gap-3">
              <h2 className="text-lg font-semibold text-text-primary">
                {language.name_pt}
                <span className="ml-2 text-sm font-normal text-text-secondary">
                  {language.native_name}
                </span>
              </h2>
              <LevelBlock level={language.level} legacyLevel={language.level_estimate} />
              {language.goal && (
                <p className="text-sm text-text-secondary">Objetivo: {language.goal}</p>
              )}
              <Link href="/languages" className="text-sm font-semibold text-primary hover:underline">
                Gerenciar idiomas
              </Link>
            </div>
          ) : (
            <EmptyState
              title="Escolha um idioma para começar."
              description="Defina o idioma principal no onboarding."
              action={
                <Link href="/onboarding" className="text-sm font-semibold text-primary hover:underline">
                  Configurar plano
                </Link>
              }
            />
          )}
        </article>

        <article className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Revisões
          </p>
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
              <Link href="/learn/review" className="text-sm font-semibold text-primary hover:underline">
                Abrir revisões
              </Link>
            </div>
          ) : (
            <EmptyState
              title="Nenhuma revisão pendente por enquanto."
              description="Itens aparecem aqui quando houver revisão agendada."
              action={
                <Link href="/learn/review" className="text-sm font-semibold text-primary hover:underline">
                  Abrir revisões
                </Link>
              }
            />
          )}
        </article>
      </section>

      {/* Prática livre — secundária ao caminho do dia */}
      <section className="mt-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="section-title">Prática livre</h2>
            <p className="mt-1 text-sm text-text-secondary">
              Extra, fora da sequência do dia. O caminho do cronograma continua sendo o foco.
            </p>
          </div>
          <Link href="/learn" className="text-sm font-semibold text-primary hover:underline">
            Ver todas
          </Link>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {practiceSlugs.map((slug) => {
            const mode = getMode(slug);
            if (!mode) return null;
            return <ModeCard key={slug} mode={mode} compact />;
          })}
        </div>
      </section>

      {/* Atividade recente */}
      <section className="mt-8 panel p-5">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Atividade recente
        </p>
        {activity.length > 0 ? (
          <ul className="mt-4 grid gap-3">
            {activity.map((session) => (
              <li key={session.id} className="border-b border-border pb-3 text-sm last:border-0 last:pb-0">
                <span className="font-medium text-text-primary">
                  {session.summary || (session.status === "completed" ? "Sessão concluída" : "Sessão de estudo")}
                </span>
                {typeof session.minutes === "number" ? (
                  <span className="text-text-secondary"> · {session.minutes} min</span>
                ) : null}
                {session.started_at ? (
                  <span className="mt-1 block text-xs text-text-secondary">
                    {new Date(session.started_at).toLocaleString("pt-BR")}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
            <EmptyState
              title="Você ainda não iniciou nenhuma prática."
              description="Abra o caminho do dia no cronograma para começar."
              action={
                <Link
                  href={next?.kind === "curriculum" ? next.href : "/cronograma"}
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--primary-hover)]"
                >
                  Abrir caminho
                </Link>
              }
            />
        )}
      </section>
    </div>
  );
}
