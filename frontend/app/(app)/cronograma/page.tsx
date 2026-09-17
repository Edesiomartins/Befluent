"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, CalendarCheck, Check, Circle, Target } from "lucide-react";
import { Button, ErrorState, Loading } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { levelShortCode } from "@/lib/levels";
import { useActiveLanguage } from "@/hooks/use-active-language";
import {
  createCurriculum,
  rescheduleCurriculum,
  useActiveCurriculum,
  useTodayInCurriculum,
} from "@/hooks/use-curriculum";
import {
  DURATIONS,
  type CurriculumBlock,
  type CurriculumWeek,
  type Duration,
  type RescheduleStrategy,
} from "@/types/curriculum";

const DAYS_PER_WEEK = 7;

const DURATION_LABELS: Record<Duration, { title: string; hint: string }> = {
  90: {
    title: "90 jornadas",
    hint: "Ritmo intensivo recomendado. Você pode avançar mais de uma jornada no mesmo dia.",
  },
  180: {
    title: "180 jornadas",
    hint: "Ritmo sustentável recomendado. Meta: B2, com mais tempo em cada nível.",
  },
};

type WeekState = "done" | "current" | "future";

/** Estado da semana derivado do dia corrente — o payload não traz os dias. */
function weekState(week: CurriculumWeek, currentDay: number | null): WeekState {
  if (currentDay == null) return "future";
  const lastDay = week.week_number * DAYS_PER_WEEK;
  const firstDay = lastDay - DAYS_PER_WEEK + 1;
  if (currentDay > lastDay) return "done";
  if (currentDay >= firstDay) return "current";
  return "future";
}

const WEEK_STATE_LABELS: Record<WeekState, string> = {
  done: "Concluída",
  current: "Em andamento",
  future: "Próximas jornadas",
};

function formatDate(value: string): string {
  // `scheduled_date` é uma data pura (sem hora): construir com `new Date(str)`
  // aplicaria fuso e poderia exibir o dia anterior.
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
  });
}

function BlockRow({ block }: { block: CurriculumBlock }) {
  const done = block.status === "completed";
  return (
    <li className="flex items-start gap-3 border-b border-border py-3 last:border-0">
      {done ? (
        <Check className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
      ) : (
        <Circle className="mt-0.5 size-4 shrink-0 text-border" aria-hidden />
      )}
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-semibold ${done ? "text-text-secondary line-through" : ""}`}>
          {block.skill_label}
        </p>
        <p className="mt-0.5 text-sm text-text-secondary">{block.topic}</p>
      </div>
      <span className="shrink-0 text-xs font-medium text-text-secondary tabular-nums">
        {block.estimated_minutes} min · {levelShortCode(block.cefr_level)}
      </span>
    </li>
  );
}

function CreateCurriculum({
  languageCode,
  onCreated,
}: {
  languageCode: string;
  onCreated: () => void;
}) {
  const [duration, setDuration] = useState<Duration>(90);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setSaving(true);
    setError("");
    try {
      await createCurriculum(languageCode, duration);
      onCreated();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível gerar seu cronograma.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="page-title">Monte seu cronograma de estudo</h1>
      <p className="mt-3 leading-7 text-text-secondary">
        O cronograma organiza jornadas de estudo (não dias de calendário obrigatórios)
        com blocos de vocabulário, gramática, pronúncia, escuta, leitura, conversação,
        escrita e revisão — partindo do nível medido no seu teste de nivelamento.
      </p>

      <fieldset className="mt-8">
        <legend className="section-title">Em quanto tempo?</legend>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {DURATIONS.map((value) => (
            <label
              key={value}
              className={`cursor-pointer rounded-xl border p-5 transition ${
                duration === value
                  ? "border-primary bg-primary-soft"
                  : "border-border bg-surface hover:border-primary/40"
              }`}
            >
              <input
                className="sr-only"
                type="radio"
                name="duration"
                value={value}
                checked={duration === value}
                onChange={() => setDuration(value)}
              />
              <span
                className={`block text-base font-bold ${duration === value ? "text-primary" : ""}`}
              >
                {DURATION_LABELS[value].title}
              </span>
              <span className="mt-1 block text-sm text-text-secondary">
                {DURATION_LABELS[value].hint}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="mt-5 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="mt-7 border-t border-border pt-6">
        <Button loading={saving} disabled={saving} onClick={() => void submit()}>
          Gerar cronograma
        </Button>
        <p className="mt-3 text-xs text-text-secondary">
          O cronograma é uma estimativa a partir do seu nivelamento. Não é garantia de
          atingir o nível-meta no prazo.
        </p>
      </div>
    </div>
  );
}

function OverdueNotice({
  curriculumId,
  overdueCount,
  onDone,
}: {
  curriculumId: string;
  overdueCount: number;
  onDone: () => void;
}) {
  const [saving, setSaving] = useState<RescheduleStrategy | null>(null);
  const [error, setError] = useState("");

  async function apply(strategy: RescheduleStrategy) {
    setSaving(strategy);
    setError("");
    try {
      await rescheduleCurriculum(curriculumId, strategy);
      onDone();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível reagendar o cronograma.",
      );
    } finally {
      setSaving(null);
    }
  }

  // Atraso não é erro: o aluno pode seguir normalmente. Por isso fica como uma
  // linha calma com as opções recolhidas, e não como alerta laranja.
  return (
    <details className="disclosure group mt-4 rounded-xl border border-border bg-surface px-5 py-4">
      <summary className="flex flex-wrap items-baseline justify-between gap-2 !text-text-primary after:!content-none">
        <span className="flex items-center gap-2 text-sm font-semibold">
          <span className="size-2 rounded-full bg-[var(--streak)]" aria-hidden />
          {overdueCount}{" "}
          {overdueCount === 1 ? "jornada atrás do ritmo" : "jornadas atrás do ritmo"}
        </span>
        <span className="text-sm font-semibold text-primary">
          <span className="group-open:hidden">Reorganizar datas</span>
          <span className="hidden group-open:inline">Fechar</span>
        </span>
      </summary>
      <p className="mt-3 text-sm leading-6 text-text-secondary">
        Isso é só ritmo recomendado — você pode continuar a próxima jornada agora. Se
        quiser realinhar as datas planejadas, escolha uma opção abaixo.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Button
          variant="secondary"
          loading={saving === "compress"}
          disabled={saving !== null}
          onClick={() => void apply("compress")}
        >
          Comprimir — manter o prazo
        </Button>
        <Button
          variant="secondary"
          loading={saving === "extend"}
          disabled={saving !== null}
          onClick={() => void apply("extend")}
        >
          Estender — empurrar as datas
        </Button>
      </div>
      <p className="mt-3 text-xs leading-5 text-text-secondary">
        Comprimir redistribui vocabulário, gramática e revisão dos dias vencidos pelos dias
        restantes e descarta o resto daqueles dias. Estender mantém tudo e adia o fim do
        cronograma em {overdueCount} {overdueCount === 1 ? "dia" : "dias"}.
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
    </details>
  );
}

export default function CronogramaPage() {
  const { code, resolved } = useActiveLanguage();
  const curriculum = useActiveCurriculum(resolved ? code : null);
  const today = useTodayInCurriculum(resolved ? code : null);

  function reloadAll() {
    void curriculum.reload();
    void today.reload();
  }

  if (!resolved || curriculum.status === "loading") {
    return <Loading label="Carregando seu cronograma" />;
  }

  if (curriculum.status === "error") {
    if (curriculum.code === "curriculum_not_found") {
      return <CreateCurriculum languageCode={code} onCreated={reloadAll} />;
    }
    // Sem nivelamento não há ponto de entrada; sem idioma configurado não há
    // nem perfil. Cada caso tem um próximo passo diferente — mandar os dois
    // para "tentar novamente" deixaria o aluno sem saída.
    const nextStep =
      curriculum.code === "placement_required"
        ? { href: "/placement-test", cta: "Fazer teste de nível" }
        : curriculum.code === "language_not_configured"
          ? { href: "/onboarding", cta: "Configurar idioma" }
          : null;

    if (nextStep) {
      return (
        <div className="mx-auto max-w-2xl">
          <h1 className="page-title">Cronograma</h1>
          <p className="mt-4 leading-7 text-text-secondary">{curriculum.error}</p>
          <Link
            href={nextStep.href}
            className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white hover:bg-[var(--primary-hover)]"
          >
            {nextStep.cta}
          </Link>
        </div>
      );
    }
    return <ErrorState message={curriculum.error} retry={reloadAll} />;
  }

  const plan = curriculum.data;
  const progress = plan.progress;
  const currentDay = today.status === "ready" ? today.data.day : null;
  const currentWeek = today.status === "ready" ? today.data.week : null;

  return (
    <div>
      <header className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <h1 className="page-title">Seu plano de {plan.duration_days} jornadas</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5">
              <Target className="size-4" aria-hidden />
              <span>
                {levelShortCode(plan.entry_level)} → {levelShortCode(plan.target_level)}
              </span>
            </span>
            {progress.next_checkpoint_week && (
              <span className="flex items-center gap-1.5">
                <CalendarCheck className="size-4" aria-hidden />
                <span>Próximo checkpoint: semana {progress.next_checkpoint_week}</span>
              </span>
            )}
          </div>
        </div>
        <p className="display-number text-3xl leading-none md:text-right">
          Dia {progress.current_day_number ?? progress.days_total} de {progress.days_total}
        </p>
      </header>

      {/* Progresso geral */}
      <section className="mt-6">
        <div
          className="h-1.5 rounded-full bg-surface-elevated"
          role="progressbar"
          aria-label="Progresso do cronograma"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress.percent_complete}
        >
          <div
            className="h-full rounded-full bg-primary transition-[width]"
            style={{ width: `${progress.percent_complete}%` }}
          />
        </div>
        <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-text-secondary">
          <span>
            {progress.days_completed}{" "}
            {progress.days_completed === 1 ? "jornada concluída" : "jornadas concluídas"} ·{" "}
            {progress.percent_complete}%
          </span>
          {progress.pace_label_pt && <span>{progress.pace_label_pt}</span>}
        </div>
        {plan.disclaimer && (
          <details className="disclosure mt-3">
            <summary>Sobre este cronograma</summary>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-text-secondary">
              {plan.disclaimer}
            </p>
          </details>
        )}
      </section>

      {progress.overdue_days > 0 && (
        <OverdueNotice
          curriculumId={plan.id}
          overdueCount={progress.overdue_days}
          onDone={reloadAll}
        />
      )}

      {/* Próxima jornada (progresso, não calendário) */}
      <section className="panel mt-6 p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="section-title">Continuar aprendendo</h2>
          {currentWeek && (
            <span className="text-sm text-text-secondary">
              Semana {currentWeek.week_number} · {currentWeek.theme}
              {currentWeek.is_checkpoint && (
                <span className="ml-2 text-xs font-semibold text-[var(--gold-ink)]">
                  Checkpoint
                </span>
              )}
            </span>
          )}
        </div>

        {today.status === "loading" && <Loading label="Carregando a próxima jornada" />}
        {today.status === "error" && (
          <ErrorState message={today.error} retry={() => void today.reload()} />
        )}

        {currentDay ? (
          <>
            <p
              className="mt-2 text-sm text-text-secondary"
              title={`Planejado originalmente para ${formatDate(currentDay.scheduled_date)} (ritmo recomendado — não bloqueia o avanço)`}
            >
              Dia {currentDay.day_number} de {progress.days_total} · {currentDay.total_minutes}{" "}
              min estimados
            </p>
            <ul className="mt-4">
              {currentDay.blocks.map((block) => (
                <BlockRow key={block.id} block={block} />
              ))}
            </ul>
            <Link
              href={`/cronograma/dia/${currentDay.id}`}
              className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white hover:bg-[var(--primary-hover)]"
            >
              {currentDay.blocks_completed > 0
                ? "Continuar aprendendo"
                : "Começar esta jornada"}
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </>
        ) : (
          today.status === "ready" && (
            <p className="mt-3 text-sm text-text-secondary">
              Você concluiu todas as jornadas deste cronograma.
            </p>
          )
        )}
      </section>

      {/* Semanas */}
      <section className="mt-8">
        <h2 className="section-title">Semanas</h2>
        <ul className="panel mt-4 divide-y divide-border overflow-hidden">
          {plan.weeks.map((week) => {
            const state = weekState(week, progress.current_day_number);
            return (
              <li
                key={week.id}
                className={`grid grid-cols-[3.5rem_minmax(0,1fr)_auto] items-baseline gap-3 px-5 py-3 text-sm ${
                  state === "current" ? "bg-primary-soft/40" : ""
                }`}
                aria-current={state === "current" ? "step" : undefined}
              >
                <span
                  className={`display-number text-lg leading-none ${
                    state === "future" ? "text-text-secondary" : "text-text-primary"
                  }`}
                >
                  {week.week_number}
                </span>
                <span className="min-w-0">
                  <span className={state === "current" ? "font-semibold" : ""}>{week.theme}</span>
                  {week.is_checkpoint && (
                    <span className="ml-2 text-xs font-semibold text-[var(--gold-ink)]">
                      Checkpoint
                    </span>
                  )}
                </span>
                <span className="flex shrink-0 items-baseline gap-3 text-xs">
                  <span className="font-semibold tabular-nums">{levelShortCode(week.cefr_focus)}</span>
                  <span
                    className={`hidden w-28 text-right sm:inline ${
                      state === "done"
                        ? "text-success"
                        : state === "current"
                          ? "font-semibold text-primary"
                          : "text-text-secondary"
                    }`}
                  >
                    {WEEK_STATE_LABELS[state]}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
