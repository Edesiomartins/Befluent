"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { DashboardSkeleton } from "@/components/dashboard-skeleton";
import { EmptyState } from "@/components/ui";

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
  } | null;
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
  }>;
};

const levelLabels: Record<string, string> = {
  iniciante: "Iniciante",
  basico: "Básico",
  intermediario: "Intermediário",
  avancado: "Avançado",
  "nao-sei": "A definir",
};

function formatLevel(value: string | null | undefined) {
  if (!value) return null;
  return levelLabels[value] ?? value;
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
  const reviews = data?.reviews_due ?? [];
  const activity = data?.recent_activity ?? [];

  return (
    <div>
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-sm font-semibold text-primary">Painel</p>
          <h1 className="page-title">Bem-vindo ao BeFluent</h1>
          <p className="mt-3 text-text-secondary">
            {hasPlan
              ? "Seu plano está ativo. Continue no seu ritmo."
              : "Organize sua rotina de estudo e avance no seu ritmo."}
          </p>
        </div>
        <Link
          href="/learn"
          className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--primary-hover)]"
        >
          Ir para prática
        </Link>
      </div>

      <section className="mt-9 grid gap-5 md:grid-cols-2">
        <article className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Idioma ativo
          </p>
          {hasPlan && language ? (
            <div className="mt-4 grid gap-2">
              <h2 className="text-xl font-semibold text-text-primary">
                {language.name_pt}
                <span className="ml-2 text-base font-normal text-text-secondary">
                  {language.native_name}
                </span>
              </h2>
              <p className="text-sm text-text-secondary">
                Nível: {formatLevel(language.level_estimate) ?? "Não informado"}
              </p>
              {language.goal && (
                <p className="text-sm text-text-secondary">Objetivo: {language.goal}</p>
              )}
              {language.minutes_per_day != null && (
                <p className="text-sm text-text-secondary">
                  Meta diária: {language.minutes_per_day} min
                </p>
              )}
              <p className="text-sm font-medium text-success">Onboarding concluído</p>
              {language.skills.length > 0 && (
                <p className="text-sm text-text-secondary">
                  Foco: {language.skills.join(", ")}
                </p>
              )}
              <Link
                href="/languages"
                className="mt-2 text-sm font-semibold text-primary hover:underline"
              >
                Gerenciar idiomas
              </Link>
            </div>
          ) : (
            <EmptyState
              title="Escolha um idioma para começar."
              description="Defina o idioma principal no onboarding ou na área de idiomas."
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
                {reviews.slice(0, 5).map((item) => (
                  <li key={item.id} className="text-sm text-text-primary">
                    {item.item_type}
                    {typeof item.payload?.term === "string"
                      ? `: ${item.payload.term}`
                      : ""}
                  </li>
                ))}
              </ul>
              <Link
                href="/learn/review"
                className="text-sm font-semibold text-primary hover:underline"
              >
                Abrir revisões
              </Link>
            </div>
          ) : (
            <EmptyState
              title="Nenhuma revisão pendente por enquanto."
              description="Quando você salvar vocabulário ou completar práticas, as revisões aparecerão aqui."
              action={
                <Link href="/learn/review" className="text-sm font-semibold text-primary hover:underline">
                  Abrir revisões
                </Link>
              }
            />
          )}
        </article>
      </section>

      <section className="mt-5 panel p-5">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Atividade recente
        </p>
        {activity.length > 0 ? (
          <ul className="mt-4 grid gap-3">
            {activity.map((session) => (
              <li key={session.id} className="text-sm text-text-primary">
                Sessão {session.status}
                {session.summary ? ` — ${session.summary}` : ""}
                {session.started_at
                  ? ` · ${new Date(session.started_at).toLocaleString("pt-BR")}`
                  : ""}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title="Você ainda não iniciou nenhuma prática."
            description="Comece por conversação, vocabulário ou uma aula guiada."
            action={
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/learn/conversation"
                  className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--primary-hover)]"
                >
                  Conversação
                </Link>
                {!hasPlan && (
                  <Link
                    href="/onboarding"
                    className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text-primary hover:bg-surface-elevated"
                  >
                    Configurar plano
                  </Link>
                )}
              </div>
            }
          />
        )}
      </section>
    </div>
  );
}
