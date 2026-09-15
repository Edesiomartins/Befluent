"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { EmptyState, Loading } from "@/components/ui";
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

      <section className="panel mt-8 grid grid-cols-2 divide-border md:grid-cols-4 md:divide-x">
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
