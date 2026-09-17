"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { EmptyState, Loading } from "@/components/ui";
import { ProgressActivityChart, type DailyActivity } from "@/components/progress-activity-chart";
import { MasteryProgressChart, type MasteryTimelinePoint } from "@/components/mastery-progress-chart";
import { levelShortCode } from "@/lib/levels";

type MasteryData = {
  status: "ready" | "calibrating" | "unavailable";
  overall_percent: number | null;
  by_skill: Array<{ skill: string; percent: number | null; label?: string }>;
  timeline: MasteryTimelinePoint[];
  cefr: { current: string; next: string; readiness_percent: number } | null;
  priorities: Array<{ skill: string; href?: string; label?: string; reason?: string }>;
};

type ProgressData = {
  vocabulary_items: number;
  study_sessions: number;
  streak_days: number;
  total_minutes: number;
  minutes_today: number;
  total_minutes_label: string;
  daily_activity?: DailyActivity;
  mastery?: MasteryData;
  recent_activity: Array<{
    id: string;
    status: string;
    summary: string | null;
    started_at: string | null;
    ended_at: string | null;
    minutes: number;
  }>;
  active_language: {
    code: string;
    name_pt: string;
    native_name: string;
    level_estimate: string | null;
    current_level: string | null;
    goal: string | null;
    skills: string[];
  } | null;
};

const skillLabels: Record<string, string> = {
  reading: "Leitura",
  listening: "Escuta",
  writing: "Escrita",
  speaking: "Fala",
  grammar: "Gramática",
  vocabulary: "Vocabulário",
};

function skillLabel(skill: string, label?: string) {
  return label ?? skillLabels[skill] ?? skill;
}

function activityLabel(session: ProgressData["recent_activity"][number]) {
  if (session.summary) return session.summary;
  if (session.status === "completed") return "Sessão concluída";
  if (session.status === "active") return "Sessão em andamento";
  return `Sessão ${session.status}`;
}

function activityDate(iso: string | null) {
  if (!iso) return "—";
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "Hoje";
  if (date.toDateString() === yesterday.toDateString()) return "Ontem";
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

export default function ProgressPage() {
  const [data, setData] = useState<ProgressData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const [periodDays, setPeriodDays] = useState<7 | 30>(7);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<ProgressData>(periodDays === 7 ? "/api/v1/progress" : "/api/v1/progress?days=30")
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar o progresso.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey, periodDays]);

  if (loading) return <Loading label="Carregando progresso" />;

  if (error) {
    return (
      <div>
        <h1 className="page-title">Seu progresso</h1>
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}
        </p>
        <button
          type="button"
          className="mt-5 min-h-11 rounded-xl bg-primary px-5 text-sm font-semibold text-white hover:bg-primary-hover"
          onClick={() => setReloadKey((key) => key + 1)}
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  const language = data?.active_language ?? null;
  const mastery = data?.mastery;
  const hasDemonstratedMastery = mastery?.status === "ready" && typeof mastery.overall_percent === "number";
  const stats = [
    {
      label: "Tempo total",
      value: data?.total_minutes_label ?? "0min",
      hint:
        (data?.minutes_today ?? 0) > 0
          ? `${data?.minutes_today} min hoje`
          : "Nenhum estudo registrado hoje",
    },
    {
      label: "Sessões",
      value: String(data?.study_sessions ?? 0),
      hint: "Registradas neste idioma",
    },
    {
      label: "Vocabulário",
      value: String(data?.vocabulary_items ?? 0),
      hint: "Itens salvos",
    },
  ];

  return (
    <div>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="page-title">Seu progresso</h1>
        </div>
        {language && (
          <p className="text-sm font-medium text-text-secondary">
            {language.name_pt}
            {language.current_level
              ? ` · ${levelShortCode(language.current_level)}`
              : language.level_estimate
                ? ` · ${language.level_estimate}`
                : ""}
          </p>
        )}
      </div>

      <section className="panel mt-8 p-6 sm:p-8">
        <p className="label">Aprendizado baseado em evidências</p>
        <div className="mt-2 flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <h2 className="font-display text-[1.75rem] font-medium leading-tight tracking-[-0.015em]">Domínio demonstrado</h2>
            {hasDemonstratedMastery ? (
              <p className="mt-3 font-display text-5xl font-medium leading-none tracking-[-0.03em]">{mastery.overall_percent}%</p>
            ) : (
              <p className="mt-3 text-sm text-text-secondary">Dados em calibração: pratique atividades com objetivo para formar uma medida confiável.</p>
            )}
          </div>
          {hasDemonstratedMastery && mastery.cefr && (
            <div className="rounded-xl border border-border bg-surface-soft px-4 py-3 sm:text-right">
              <p className="text-xs text-text-secondary">Caminho CEFR</p>
              <p className="mt-1 font-display text-2xl leading-none">{mastery.cefr.current} → {mastery.cefr.next}</p>
              <p className="mt-2 text-xs text-text-secondary">{mastery.cefr.readiness_percent}% de prontidão</p>
            </div>
          )}
        </div>
        {hasDemonstratedMastery && mastery.by_skill.length > 0 && (
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            {mastery.by_skill.map((skill) => (
              <div key={skill.skill}>
                <div className="flex justify-between gap-4 text-sm"><span className="font-medium">{skillLabel(skill.skill, skill.label)}</span><span className="tabular-nums text-text-secondary">{skill.percent}%</span></div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-soft"><div className="h-full rounded-full bg-primary" style={{ width: `${skill.percent}%` }} /></div>
              </div>
            ))}
          </div>
        )}
        {hasDemonstratedMastery && mastery.priorities.length > 0 && (
          <div className="mt-6 border-t border-border pt-5">
            <p className="text-sm font-semibold">Prioridades para avançar</p>
            <ul className="mt-2 grid gap-2 text-sm">
              {mastery.priorities.slice(0, 3).map((priority, index) => (
                <li key={`${priority.skill}-${index}`}><Link className="font-medium text-primary hover:underline" href={priority.href ?? "/learn"}>{priority.label ?? priority.reason ?? skillLabel(priority.skill)}</Link></li>
              ))}
            </ul>
          </div>
        )}
        {hasDemonstratedMastery && <MasteryProgressChart timeline={mastery.timeline} />}
      </section>

      <section className="panel mt-8 grid grid-cols-2 divide-border md:grid-cols-4 md:divide-x" aria-label="Métricas de hábito">
        {[
          ...stats,
          {
            label: "Dias seguidos",
            value: String(data?.streak_days ?? 0),
            hint: "Dias com sessão registrada",
          },
        ].map(({ label, value, hint }) => (
          <div key={label} className="p-5 md:p-6">
            <p className="text-sm text-text-secondary">{label}</p>
            <p className="display-number mt-2 text-4xl leading-none">{value}</p>
            <p className="mt-2 text-xs text-text-secondary">{hint}</p>
          </div>
        ))}
      </section>

      <section className="panel mt-8 p-6 sm:p-8">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
          <div>
            <p className="label">Ritmo de estudo</p>
            <h2 className="section-title mt-2">Minutos por dia</h2>
          </div>
          {language && (
            <p className="text-sm text-text-secondary">Somente {language.name_pt}</p>
          )}
        </div>
        <div className="mt-5 inline-flex rounded-xl border border-border p-1" aria-label="Período do gráfico">
          {([7, 30] as const).map((days) => (
            <button key={days} type="button" aria-pressed={periodDays === days} onClick={() => setPeriodDays(days)} className={`min-h-9 rounded-lg px-3 text-sm font-semibold ${periodDays === days ? "bg-primary text-white" : "text-text-secondary hover:text-text-primary"}`}>{days} dias</button>
          ))}
        </div>
        <ProgressActivityChart activity={data?.daily_activity} />
      </section>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_.9fr]">
        <section className="panel p-6">
          <h2 className="section-title">Foco do plano</h2>
          {language?.goal || (language?.skills?.length ?? 0) > 0 ? (
            <div className="mt-4 grid gap-4">
              {language?.goal && (
                <p className="text-sm">
                  <span className="text-text-secondary">Objetivo: </span>
                  <span className="font-semibold">{language.goal}</span>
                </p>
              )}
              <ul className="divide-y divide-border border-y border-border">
                {(language?.skills ?? []).map((skill) => (
                  <li key={skill} className="py-2.5 text-sm font-medium">
                    {skill}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <EmptyState
              title="Nenhum foco definido ainda."
              description="Conclua o onboarding para registrar objetivo e habilidades."
              action={
                <Link href="/onboarding" className="text-sm font-semibold text-primary hover:underline">
                  Configurar plano
                </Link>
              }
            />
          )}
        </section>

        <section className="panel p-6">
          <h2 className="section-title">Atividade recente</h2>
          {(data?.recent_activity?.length ?? 0) > 0 ? (
            <div className="mt-4 divide-y divide-border">
              {data!.recent_activity.map((session) => (
                <div
                  key={session.id}
                  className="grid grid-cols-[4.5rem_1fr_auto] gap-3 py-4 text-sm first:pt-0 last:pb-0"
                >
                  <span className="text-text-secondary">{activityDate(session.started_at)}</span>
                  <span className="font-medium">{activityLabel(session)}</span>
                  <span className="text-text-secondary">{session.minutes} min</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Nenhuma sessão registrada."
              description="Quando você praticar, as sessões aparecerão aqui."
              action={
                <Link href="/learn" className="text-sm font-semibold text-primary hover:underline">
                  Ir para prática
                </Link>
              }
            />
          )}
        </section>
      </div>
    </div>
  );
}
