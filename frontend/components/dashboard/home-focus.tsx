"use client";

import Link from "next/link";
import { deriveDailyMission } from "@/lib/journey";
import type { TodayPayload } from "@/types/curriculum";
import type { DashboardData } from "@/components/dashboard/types";

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

  return (
    <div>
      <header>
        <h1 className="page-title">{hasPlan ? "Seu estudo de hoje" : "Bem-vindo ao BeFluent"}</h1>
        {language && (
          <p className="mt-2 text-text-secondary">
            {language.name_pt}
            <span className="ml-2 text-sm">{language.native_name}</span>
          </p>
        )}
        {!hasPlan && (
          <p className="mt-2 text-text-secondary">
            Configure seu plano para liberar o caminho diário.
          </p>
        )}
      </header>

      <div className="mt-8 grid items-start gap-5 lg:grid-cols-[minmax(0,1.5fr)_16rem]">
        <section className="panel p-6 sm:p-8" aria-labelledby="daily-mission-title">
          <p className="text-sm font-semibold text-text-secondary">Missão de hoje</p>
          <h2 id="daily-mission-title" className="page-title mt-3">
            {title}
          </h2>
          {mission?.subtitle && mission.subtitle !== mission.title && (
            <p className="mt-3 max-w-xl text-sm leading-6 text-text-secondary">{mission.subtitle}</p>
          )}
          <Link
            href={href}
            className="mt-7 inline-flex min-h-14 items-center rounded-2xl bg-primary px-6 text-lg font-semibold text-white hover:bg-[var(--primary-hover)]"
          >
            {label}
          </Link>
        </section>

        <aside className="grid grid-cols-2 gap-3 lg:grid-cols-1" aria-label="Sequência e meta diária">
          <div className="panel p-5">
            <p className="text-xs font-semibold text-text-secondary">Sequência</p>
            <p className="display-number mt-2 text-3xl leading-none">{streak}</p>
            <p className="mt-1 text-sm text-text-secondary">dias seguidos</p>
          </div>
          <div className="panel p-5">
            <p className="text-xs font-semibold text-text-secondary">Meta diária</p>
            <p className="display-number mt-2 text-3xl leading-none">{minutes ?? "—"}</p>
            <p className="mt-1 text-sm text-text-secondary">minutos</p>
          </div>
        </aside>
      </div>

      <nav className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold" aria-label="Mais do estudo">
        <Link href="/dashboard/estudo" className="text-primary hover:underline">
          Idioma e plano
        </Link>
        <Link href="/dashboard/pratica" className="text-primary hover:underline">
          Prática e revisões
        </Link>
        <Link href="/progress" className="text-primary hover:underline">
          Progresso
        </Link>
      </nav>
    </div>
  );
}
