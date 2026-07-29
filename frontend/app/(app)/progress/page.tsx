"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BarChart3, Clock, Flame, Trophy } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { EmptyState, Loading } from "@/components/ui";
import { modeColorClasses } from "@/lib/modes";
import { levelShortCode } from "@/lib/levels";

type ProgressData = {
  vocabulary_items: number;
  study_sessions: number;
  streak_days: number;
  total_minutes: number;
  minutes_today: number;
  total_minutes_label: string;
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

  useEffect(() => {
    let active = true;
    api<ProgressData>("/api/v1/progress")
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
  }, []);

  if (loading) return <Loading label="Carregando progresso" />;

  if (error) {
    return (
      <div>
        <h1 className="page-title">Seu progresso</h1>
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}
        </p>
      </div>
    );
  }

  const language = data?.active_language ?? null;
  const stats = [
    {
      icon: Clock,
      color: "primary" as const,
      label: "Tempo total",
      value: data?.total_minutes_label ?? "0min",
      hint:
        (data?.minutes_today ?? 0) > 0
          ? `${data?.minutes_today} min hoje`
          : "Nenhum estudo registrado hoje",
    },
    {
      icon: Trophy,
      color: "gold" as const,
      label: "Sessões",
      value: String(data?.study_sessions ?? 0),
      hint: "Registradas neste idioma",
    },
    {
      icon: BarChart3,
      color: "violet" as const,
      label: "Vocabulário",
      value: String(data?.vocabulary_items ?? 0),
      hint: "Itens salvos",
    },
  ];

  return (
    <div>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-semibold text-primary">Acompanhamento</p>
          <h1 className="mt-2 page-title">Seu progresso</h1>
          <p className="mt-3 text-text-secondary">
            Dados reais da sua conta — sem estimativas inventadas.
          </p>
        </div>
        {language && (
          <p className="rounded-xl border border-border bg-surface px-4 py-2 text-sm font-medium">
            {language.name_pt}
            {language.current_level
              ? ` · ${levelShortCode(language.current_level)}`
              : language.level_estimate
                ? ` · ${language.level_estimate}`
                : ""}
          </p>
        )}
      </div>

      <section className="mt-8 grid gap-4 sm:grid-cols-3">
        {stats.map(({ icon: Icon, color, label, value, hint }) => {
          const colors = modeColorClasses[color];
          return (
            <div key={label} className="panel p-5">
              <span className={`grid size-11 place-items-center rounded-xl ${colors.bg} ${colors.text}`}>
                <Icon className="size-5" aria-hidden />
              </span>
              <p className="mt-4 text-sm text-text-secondary">{label}</p>
              <p className="mt-1 text-3xl font-bold tracking-tight">{value}</p>
              <p className="mt-1 text-xs text-text-secondary">{hint}</p>
            </div>
          );
        })}
      </section>

      <div className="mt-4 panel flex items-center gap-3 p-4">
        <span className="grid size-10 place-items-center rounded-full bg-[var(--streak-soft)] text-[var(--streak-shadow)]">
          <Flame className="size-5 fill-current" aria-hidden />
        </span>
        <div>
          <p className="text-lg font-bold tracking-tight">{data?.streak_days ?? 0} dia(s) seguidos</p>
          <p className="text-sm text-text-secondary">
            Sequência baseada em dias com sessão de estudo registrada.
          </p>
        </div>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_.9fr]">
        <section className="panel p-6">
          <h2 className="section-title">Foco do plano</h2>
          <p className="mt-2 text-sm text-text-secondary">
            Habilidades e objetivo definidos no onboarding.
          </p>
          {language?.goal || (language?.skills?.length ?? 0) > 0 ? (
            <div className="mt-6 grid gap-3">
              {language?.goal && (
                <p className="text-sm">
                  <span className="text-text-secondary">Objetivo: </span>
                  <span className="font-semibold">{language.goal}</span>
                </p>
              )}
              <ul className="grid gap-2">
                {(language?.skills ?? []).map((skill) => (
                  <li
                    key={skill}
                    className="rounded-xl border border-border bg-[var(--surface-soft)] px-4 py-3 text-sm font-medium"
                  >
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
