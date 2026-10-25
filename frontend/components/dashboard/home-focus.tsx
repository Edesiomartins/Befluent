"use client";

import Link from "next/link";
import { ArrowRight, CalendarRange, Clock, Flame, Layers, RotateCcw, Sparkles, TrendingUp } from "lucide-react";
import { deriveDailyMission } from "@/lib/journey";
import { levelShortCode } from "@/lib/levels";
import type { TodayPayload } from "@/types/curriculum";
import type { DashboardData } from "@/components/dashboard/types";

function nextReviewText(review: DashboardData["reviews_due"][number] | undefined): string | null {
  if (!review) return null;
  if (typeof review.payload?.term === "string" && review.payload.term.trim()) {
    return review.payload.term.trim();
  }
  if (typeof review.payload?.prompt === "string" && review.payload.prompt.trim()) {
    return review.payload.prompt.trim();
  }
  return review.item_type || null;
}

export function HomeFocus({
  data,
  today,
}: {
  data: DashboardData;
  today: TodayPayload | null;
}) {
  const language = data.active_language;
  const hasPlan = Boolean(language && data.onboarding_completed);
  const mission = today?.day
    ? deriveDailyMission({
        day: today.day,
        weekTheme: today.week?.theme,
        languageName: language?.name_pt || "Seu idioma",
        level: today.week?.cefr_focus,
      })
    : null;
  const title = mission?.title || data.next_activity.title;
  const href = mission ? `/cronograma/dia/${mission.day_id}` : data.next_activity.href;
  const label = hasPlan ? "Continuar a missão de hoje" : data.next_activity.cta;
  const streak = data.progress?.streak_days ?? 0;
  const minutes = data.day_plan?.minutes_per_day;
  const reviews = data.reviews_due ?? [];
  const reviewsCount = Math.max(data.reviews_due_count ?? 0, reviews.length);
  const firstReview = nextReviewText(reviews[0]);
  const week = today?.week ?? null;
  const curriculumProgress = today?.curriculum?.progress ?? null;

  return (
    <div className="grid gap-6">
      <header className="flex flex-col justify-between gap-3 border-b border-border pb-5 sm:flex-row sm:items-end">
        <div>
          <h1 className="page-title">{hasPlan ? "Seu estudo de hoje" : "Bem-vindo ao BeFluent"}</h1>
          {!hasPlan && (
            <p className="mt-1.5 text-sm text-text-secondary">
              Configure seu plano para liberar o caminho diário.
            </p>
          )}
        </div>
        {language && (
          <p className="inline-flex items-center gap-2 self-start rounded-full border border-border bg-surface px-3.5 py-1.5 text-sm font-medium text-text-primary shadow-[0_1px_2px_rgba(15,23,42,0.03)] sm:self-auto">
            <span className="size-2 rounded-full bg-primary" aria-hidden />
            <span>{language.name_pt}</span>
            <span className="text-xs text-text-secondary">{language.native_name}</span>
          </p>
        )}
      </header>

      <div className="grid items-stretch gap-5 lg:grid-cols-[minmax(0,1.65fr)_17.5rem]">
        <section
          className="command-panel relative flex flex-col justify-between overflow-hidden p-6 sm:p-8"
          aria-labelledby="daily-mission-title"
        >
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="inline-flex items-center gap-1.5 rounded-full border border-white/12 bg-white/8 px-3 py-1 text-xs font-semibold text-[#93c5fd]">
                <Sparkles className="size-3.5" aria-hidden />
                <span>Missão de hoje</span>
              </p>
              {today?.day && (
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium tabular-nums text-[var(--command-muted)]">
                  Jornada {today.day.day_number}
                </span>
              )}
            </div>
            <h2
              id="daily-mission-title"
              className="mt-4 text-2xl font-semibold leading-tight tracking-[-0.025em] text-white sm:text-3xl"
            >
              {title}
            </h2>
            {mission?.subtitle && mission.subtitle !== mission.title ? (
              <p className="mt-2.5 max-w-xl text-sm leading-6 text-[var(--command-muted)]">
                {mission.subtitle}
              </p>
            ) : (
              data.next_activity.description && (
                <p className="mt-2.5 max-w-xl text-sm leading-6 text-[var(--command-muted)]">
                  {data.next_activity.description}
                </p>
              )
            )}
          </div>

          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-[var(--command-border)] pt-5">
            <Link
              href={href}
              className="inline-flex min-h-12 items-center gap-2.5 rounded-xl bg-primary px-6 text-sm font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.25),inset_0_1px_0_rgba(255,255,255,0.2)] transition-colors hover:bg-[var(--primary-hover)]"
            >
              <span>{label}</span>
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
        </section>

        <aside
          className="grid grid-cols-2 gap-3.5 lg:grid-cols-1"
          aria-label="Sequência e meta diária"
        >
          <div className="panel flex flex-col justify-between p-5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-text-secondary">Sequência</p>
              <span className="grid size-7 place-items-center rounded-lg bg-[var(--streak-soft)] text-streak">
                <Flame className="size-3.5" aria-hidden />
              </span>
            </div>
            <div className="mt-3">
              <p className="display-number text-3xl leading-none text-text-primary">{streak}</p>
              <p className="mt-1.5 text-xs font-medium text-text-secondary">dias seguidos</p>
            </div>
          </div>
          <div className="panel flex flex-col justify-between p-5">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-semibold text-text-secondary">Meta diária</p>
              <span className="grid size-7 place-items-center rounded-lg bg-primary-soft text-primary">
                <Clock className="size-3.5" aria-hidden />
              </span>
            </div>
            <div className="mt-3">
              <p className="display-number text-3xl leading-none text-text-primary">
                {minutes ?? "—"}
              </p>
              <p className="mt-1.5 text-xs font-medium text-text-secondary">minutos</p>
            </div>
          </div>
        </aside>
      </div>

      <nav
        className="panel flex flex-wrap items-center gap-2 p-2.5 text-sm font-semibold"
        aria-label="Mais do estudo"
      >
        <Link
          href="/dashboard/estudo"
          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3.5 py-2 text-text-primary transition-colors hover:bg-[var(--surface-soft)] hover:text-primary"
        >
          <Layers className="size-4 text-primary" aria-hidden />
          <span>Idioma e plano</span>
        </Link>
        <Link
          href="/dashboard/pratica"
          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3.5 py-2 text-text-primary transition-colors hover:bg-[var(--surface-soft)] hover:text-primary"
        >
          <Sparkles className="size-4 text-primary" aria-hidden />
          <span>Prática e revisões</span>
        </Link>
        <Link
          href="/progress"
          className="inline-flex min-h-10 items-center gap-2 rounded-lg px-3.5 py-2 text-text-primary transition-colors hover:bg-[var(--surface-soft)] hover:text-primary"
        >
          <TrendingUp className="size-4 text-primary" aria-hidden />
          <span>Progresso</span>
        </Link>
      </nav>

      <section
        className="grid gap-4 md:grid-cols-2"
        aria-label="Panorama de revisões e semana"
      >
        <div className="panel p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="label">Revisões de hoje</h2>
            <RotateCcw className="size-4 text-text-secondary" aria-hidden />
          </div>
          {reviewsCount > 0 ? (
            <div className="mt-3">
              <p className="text-base font-semibold text-text-primary tabular-nums">
                {reviewsCount}{" "}
                {reviewsCount === 1 ? "revisão pendente hoje" : "revisões pendentes hoje"}
              </p>
              {firstReview && (
                <p className="mt-1 text-sm text-text-secondary">
                  Próximo item: <span className="font-medium text-text-primary">{firstReview}</span>
                </p>
              )}
            </div>
          ) : (
            <div className="mt-3">
              <p className="text-sm font-semibold text-text-primary">
                Sem revisões vencidas agora
              </p>
              <p className="mt-1 text-xs leading-5 text-text-secondary">
                Novos itens entram na fila conforme você avança nas missões.
              </p>
            </div>
          )}
        </div>

        <div className="panel p-5">
          <div className="flex items-center justify-between gap-2">
            <h2 className="label">Trilha da semana</h2>
            <CalendarRange className="size-4 text-text-secondary" aria-hidden />
          </div>
          {week ? (
            <div className="mt-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-base font-semibold text-text-primary">
                  Semana {week.week_number} · {week.theme}
                </p>
                {week.cefr_focus && (
                  <span className="tech-badge">{levelShortCode(week.cefr_focus)}</span>
                )}
              </div>
              {curriculumProgress && (
                <p className="mt-1 text-xs font-medium tabular-nums text-text-secondary">
                  {curriculumProgress.days_completed} de {curriculumProgress.days_total} jornadas concluídas ({curriculumProgress.percent_complete}%)
                </p>
              )}
            </div>
          ) : (
            <div className="mt-3">
              <p className="text-sm font-semibold text-text-primary">
                Trilha semanal ainda não iniciada
              </p>
              <p className="mt-1 text-xs leading-5 text-text-secondary">
                O resumo da semana aparece assim que houver uma jornada ativa no cronograma.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
