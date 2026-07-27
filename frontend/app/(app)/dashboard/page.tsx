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
  }>;
};

const levelLabels: Record<string, string> = {
  iniciante: "Iniciante",
  basico: "Básico",
  intermediario: "Intermediário",
  avancado: "Avançado",
  "nao-sei": "A definir",
};

const practiceModes = [
  { href: "/learn/conversation", title: "Conversação", blurb: "Dialogue com correção." },
  { href: "/learn/vocabulary", title: "Vocabulário", blurb: "Palavras em contexto." },
  { href: "/learn/review", title: "Revisão", blurb: "Itens agendados." },
  { href: "/learn/guided", title: "Aula guiada", blurb: "Sequência estruturada." },
  { href: "/learn/listening", title: "Audição", blurb: "Compreensão oral." },
  { href: "/learn/writing", title: "Escrita", blurb: "Produza e corrija." },
];

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
  const next = data?.next_activity;
  const dayPlan = data?.day_plan;
  const progress = data?.progress;
  const reviews = data?.reviews_due ?? [];
  const activity = data?.recent_activity ?? [];

  return (
    <div>
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-sm font-semibold text-primary">Painel</p>
          <h1 className="page-title">Bem-vindo ao BeFluent</h1>
          <p className="mt-3 text-text-secondary">
            {hasPlan
              ? "Seu próximo passo e o plano do dia estão abaixo."
              : "Configure seu plano para desbloquear recomendações."}
          </p>
        </div>
      </div>

      {/* Próxima atividade | Plano do dia */}
      <section className="mt-8 grid gap-5 lg:grid-cols-2">
        <article className="rounded-xl bg-[var(--primary-deep)] p-6 text-white">
          <p className="text-xs font-semibold uppercase tracking-[.14em] text-white/60">
            Próxima atividade
          </p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight">{next?.title}</h2>
          <p className="mt-2 text-sm leading-6 text-white/70">{next?.description}</p>
          {next && (
            <Link
              href={next.href}
              className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-[var(--primary-deep)] hover:bg-white/90"
            >
              {next.cta}
            </Link>
          )}
        </article>

        <article className="panel p-6">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Plano do dia
          </p>
          {hasPlan ? (
            <div className="mt-4 grid gap-3">
              {dayPlan?.minutes_per_day != null && (
                <p className="text-sm text-text-secondary">
                  Meta: <span className="font-semibold text-text-primary">{dayPlan.minutes_per_day} min</span>
                </p>
              )}
              <ul className="grid gap-2">
                {(dayPlan?.items ?? []).map((item) => (
                  <li
                    key={item.label}
                    className="flex items-start gap-2 text-sm text-text-primary"
                  >
                    <span
                      className={`mt-1 inline-block size-2 shrink-0 rounded-full ${
                        item.done ? "bg-success" : "bg-border"
                      }`}
                      aria-hidden
                    />
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

      {/* Idioma ativo | Progresso | Revisões */}
      <section className="mt-5 grid gap-5 md:grid-cols-3">
        <article className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Idioma ativo
          </p>
          {hasPlan && language ? (
            <div className="mt-4 grid gap-2">
              <h2 className="text-lg font-semibold text-text-primary">
                {language.name_pt}
                <span className="ml-2 text-sm font-normal text-text-secondary">
                  {language.native_name}
                </span>
              </h2>
              <p className="text-sm text-text-secondary">
                Nível: {formatLevel(language.level_estimate) ?? "Não informado"}
              </p>
              {language.goal && (
                <p className="text-sm text-text-secondary">Objetivo: {language.goal}</p>
              )}
              <p className="text-sm font-medium text-success">Onboarding concluído</p>
              <Link href="/languages" className="mt-1 text-sm font-semibold text-primary hover:underline">
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
            Progresso
          </p>
          <div className="mt-4 grid gap-3">
            <p className="text-sm text-text-secondary">
              Vocabulário:{" "}
              <span className="font-semibold text-text-primary">
                {progress?.vocabulary_items ?? 0}
              </span>
            </p>
            <p className="text-sm text-text-secondary">
              Sessões:{" "}
              <span className="font-semibold text-text-primary">
                {progress?.study_sessions ?? 0}
              </span>
            </p>
            <p className="text-sm text-text-secondary">
              Sequência:{" "}
              <span className="font-semibold text-text-primary">
                {progress?.streak_days ?? 0} dia(s)
              </span>
            </p>
            <Link href="/progress" className="text-sm font-semibold text-primary hover:underline">
              Ver progresso
            </Link>
          </div>
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

      {/* Pratique agora */}
      <section className="mt-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="section-title">Pratique agora</h2>
            <p className="mt-1 text-sm text-text-secondary">Escolha uma atividade para começar.</p>
          </div>
          <Link href="/learn" className="text-sm font-semibold text-primary hover:underline">
            Ver todas
          </Link>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {practiceModes.map((mode) => (
            <Link
              key={mode.href}
              href={mode.href}
              className="panel group p-4 transition hover:border-primary hover:bg-primary/[0.03]"
            >
              <h3 className="font-semibold group-hover:text-primary">{mode.title}</h3>
              <p className="mt-1 text-sm text-text-secondary">{mode.blurb}</p>
            </Link>
          ))}
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
                  Sessão {session.status}
                </span>
                {session.summary ? (
                  <span className="text-text-secondary"> — {session.summary}</span>
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
            description="Comece por conversação, vocabulário ou uma aula guiada."
            action={
              <Link
                href="/learn/conversation"
                className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--primary-hover)]"
              >
                Conversação
              </Link>
            }
          />
        )}
      </section>
    </div>
  );
}
