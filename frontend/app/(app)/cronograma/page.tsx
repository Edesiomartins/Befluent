"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, ArrowRight, CalendarCheck, Check, Circle, Target } from "lucide-react";
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
    title: "90 dias",
    hint: "Ritmo intensivo. Meta: subir dois subníveis a partir do seu nível de entrada.",
  },
  180: {
    title: "180 dias",
    hint: "Ritmo sustentável. Meta: B2, com mais tempo em cada nível.",
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
  future: "A seguir",
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
      <p className="text-sm font-semibold text-primary">Cronograma</p>
      <h1 className="mt-2 page-title">Monte seu cronograma de estudo</h1>
      <p className="mt-3 leading-7 text-text-secondary">
        O cronograma organiza cada dia com blocos de vocabulário, gramática, pronúncia,
        escuta, leitura, conversação, escrita e revisão — partindo do nível medido no
        seu teste de nivelamento.
      </p>

      <fieldset className="mt-8">
        <legend className="section-title">Em quanto tempo?</legend>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {DURATIONS.map((value) => (
            <label
              key={value}
              className={`cursor-pointer rounded-xl border-2 p-5 transition ${
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

  return (
    <section className="mt-5 rounded-2xl border border-warning/30 bg-warning/5 p-5" role="alert">
      <h2 className="flex items-center gap-2 font-semibold text-warning">
        <AlertTriangle className="size-5 shrink-0" aria-hidden />
        {overdueCount} {overdueCount === 1 ? "dia atrasado" : "dias atrasados"}
      </h2>
      <p className="mt-2 text-sm leading-6 text-text-secondary">
        Você pode recuperar de duas formas. Nenhuma delas apaga o que você já concluiu.
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
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
    </section>
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
            className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
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
      <p className="text-sm font-semibold text-primary">Cronograma</p>
      <h1 className="mt-2 page-title">Seu plano de {plan.duration_days} dias</h1>

      {/* Progresso geral */}
      <section className="panel mt-7 p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <p className="text-lg font-semibold">
            Dia {progress.current_day_number ?? progress.days_total} de {progress.days_total}
          </p>
          <p className="flex items-center gap-2 text-sm text-text-secondary">
            <Target className="size-4" aria-hidden />
            {levelShortCode(plan.entry_level)} → {levelShortCode(plan.target_level)}
          </p>
        </div>
        <div className="mt-3 h-2.5 rounded-full bg-surface-elevated">
          <div
            className="h-full rounded-full bg-success transition-[width]"
            style={{ width: `${progress.percent_complete}%` }}
          />
        </div>
        <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm text-text-secondary">
          <span>
            {progress.days_completed} {progress.days_completed === 1 ? "dia" : "dias"} concluídos ·{" "}
            {progress.percent_complete}%
          </span>
          {progress.next_checkpoint_week && (
            <span className="flex items-center gap-1.5">
              <CalendarCheck className="size-4" aria-hidden />
              Próximo checkpoint: semana {progress.next_checkpoint_week}
            </span>
          )}
        </div>
        <p className="mt-4 border-t border-border pt-4 text-xs leading-5 text-text-secondary">
          {plan.disclaimer}
        </p>
      </section>

      {progress.overdue_days > 0 && (
        <OverdueNotice
          curriculumId={plan.id}
          overdueCount={progress.overdue_days}
          onDone={reloadAll}
        />
      )}

      {/* Dia de hoje */}
      <section className="panel mt-5 p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="section-title">Hoje</h2>
          {currentWeek && (
            <span className="text-sm text-text-secondary">
              Semana {currentWeek.week_number} · {currentWeek.theme}
              {currentWeek.is_checkpoint && (
                <span className="ml-2 rounded-md bg-[var(--gold-soft)] px-2 py-1 text-xs font-semibold text-[var(--gold-ink)]">
                  Checkpoint
                </span>
              )}
            </span>
          )}
        </div>

        {today.status === "loading" && <Loading label="Carregando o dia de hoje" />}
        {today.status === "error" && (
          <ErrorState message={today.error} retry={() => void today.reload()} />
        )}

        {currentDay ? (
          <>
            <p className="mt-3 text-sm text-text-secondary">
              Dia {currentDay.day_number} · {formatDate(currentDay.scheduled_date)} ·{" "}
              {currentDay.total_minutes} min estimados
            </p>
            <ul className="mt-4">
              {currentDay.blocks.map((block) => (
                <BlockRow key={block.id} block={block} />
              ))}
            </ul>
            <Link
              href={`/cronograma/dia/${currentDay.id}`}
              className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
            >
              {currentDay.blocks_completed > 0 ? "Continuar o dia" : "Começar o dia"}
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          </>
        ) : (
          today.status === "ready" && (
            <p className="mt-3 text-sm text-text-secondary">
              Você concluiu todos os dias deste cronograma.
            </p>
          )
        )}
      </section>

      {/* Semanas */}
      <section className="mt-8">
        <h2 className="section-title">Semanas</h2>
        <ul className="mt-4 grid gap-2">
          {plan.weeks.map((week) => {
            const state = weekState(week, progress.current_day_number);
            return (
              <li
                key={week.id}
                className={`panel flex flex-wrap items-center justify-between gap-3 p-4 ${
                  state === "current" ? "border-primary" : ""
                }`}
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold">
                    Semana {week.week_number}
                    {week.is_checkpoint && (
                      <span className="ml-2 rounded-md bg-[var(--gold-soft)] px-2 py-0.5 text-xs font-semibold text-[var(--gold-ink)]">
                        Checkpoint
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 text-sm text-text-secondary">{week.theme}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3 text-sm">
                  <span className="font-semibold text-primary">
                    {levelShortCode(week.cefr_focus)}
                  </span>
                  <span
                    className={
                      state === "done"
                        ? "text-success"
                        : state === "current"
                          ? "font-semibold"
                          : "text-text-secondary"
                    }
                  >
                    {WEEK_STATE_LABELS[state]}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
