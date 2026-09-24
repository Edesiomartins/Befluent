"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Check, Lock } from "lucide-react";
import { LessonContent } from "@/components/lesson-modes";
import { Button, ErrorState, Loading, Note } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { coachFor } from "@/lib/coach";
import { deriveDailyMission, journeyPhaseLabel } from "@/lib/journey";
import { levelShortCode } from "@/lib/levels";
import { activityIsAcknowledgement } from "@/lib/teaching-response";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useCurriculumDay } from "@/hooks/use-curriculum";
import type { LessonEnvelope } from "@/types/lesson";
import type {
  BlockLesson,
  CompleteBlockResponse,
  CurriculumBlock,
  DayLearningObjective,
  LessonThread,
  StartBlockResponse,
} from "@/types/curriculum";
import { TeachingActivityBody, TeachingAnswerFeedback } from "@/components/teaching-activity";
import type { SliceSession } from "@/types/teaching";

/**
 * O que este bloco herdou dos anteriores. É a peça que torna a sequência
 * visível: sem ela, cinco blocos sobre o mesmo tema parecem cinco lições
 * independentes, mesmo quando o conteúdo já vem encadeado do backend.
 */
function ThreadBanner({ lesson }: { lesson: BlockLesson }) {
  const thread = lesson.thread;
  const carried = thread?.carried_terms ?? [];
  const recycled = thread?.recycled_terms ?? [];
  if (carried.length === 0 && recycled.length === 0) return null;

  const origin = thread?.sources?.length ? thread.sources.join(" → ") : "";

  return (
    <div
      className="mb-6 border-l-2 border-primary/40 pl-4"
      title={
        [
          origin ? `Origem: ${origin}` : "",
          thread?.guaranteed === false
            ? "Conteúdo de biblioteca: o reuso destes itens é sugerido, não garantido dentro do material."
            : "",
        ]
          .filter(Boolean)
          .join(" ")
      }
    >
      <p className="label">Da etapa anterior</p>
      {carried.length > 0 && (
        <p className="mt-2 text-sm leading-6 text-text-secondary">
          Você vai usar novamente:{" "}
          <span className="font-semibold text-text-primary">{carried.join(" · ")}</span>
        </p>
      )}
      {recycled.length > 0 && (
        <p className="mt-1 text-sm leading-6 text-text-secondary">
          Retomando da semana: {recycled.join(", ")}
        </p>
      )}
    </div>
  );
}

/** Léxico que o dia inteiro já construiu, mostrado na coluna do caminho. */
function DayThread({ thread }: { thread: LessonThread }) {
  if (thread.terms.length === 0 && thread.patterns.length === 0) return null;
  return (
    <div className="mt-6 border-t border-border pt-5">
      <p className="label">Vocabulário do dia</p>
      {thread.terms.length > 0 && (
        <ul className="mt-2 grid gap-1">
          {thread.terms.map((item) => (
            <li key={item.term} className="text-sm leading-5">
              <span className="font-semibold">{item.term}</span>
              {item.translation && (
                <span className="text-text-secondary"> · {item.translation}</span>
              )}
            </li>
          ))}
        </ul>
      )}
      {thread.patterns.length > 0 && (
        <p className="mt-2.5 text-xs leading-5 text-text-secondary">
          Estruturas: {thread.patterns.join(" · ")}
        </p>
      )}
    </div>
  );
}

/** Fila de revisão servida pelo bloco `review`, direto do SRS. */
function ReviewQueue({ lesson }: { lesson: BlockLesson }) {
  const items = lesson.items ?? [];
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (lesson.queue_empty || items.length === 0) {
    return (
      <div className="panel p-6">
        <h2 className="section-title">Nenhuma revisão vencida agora</h2>
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          {lesson.empty_notice ??
            "Nenhuma revisão está vencida agora. Seu próximo conteúdo de revisão aparecerá no momento adequado."}
        </p>
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          Você pode concluir esta consolidação e seguir — sem inventar itens na fila.
        </p>
      </div>
    );
  }

  if (index >= items.length) {
    return (
      <div className="panel p-6" role="status">
        <h2 className="section-title">Revisão concluída</h2>
        <p className="mt-3 text-sm text-text-secondary">
          Você respondeu {items.length} {items.length === 1 ? "item" : "itens"}. O
          agendamento foi atualizado.
        </p>
      </div>
    );
  }

  const item = items[index];
  const prompt =
    (typeof item.payload?.term === "string" && item.payload.term) ||
    (typeof item.payload?.prompt === "string" && item.payload.prompt) ||
    item.item_type;
  const answer =
    (typeof item.payload?.translation_pt === "string" && item.payload.translation_pt) ||
    (typeof item.payload?.answer === "string" && item.payload.answer) ||
    "Revise este item e avalie sua lembrança.";

  async function rate(rating: string) {
    setSaving(true);
    setError("");
    try {
      await api(`/api/v1/reviews/${item.review_item_id}/answer`, {
        method: "POST",
        body: { rating },
      });
      setIndex((value) => value + 1);
      setRevealed(false);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível registrar a avaliação.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <p className="mb-3 text-sm text-text-secondary">
        {items.length - index}{" "}
        {items.length - index === 1 ? "item restante" : "itens restantes"} na fila
        {typeof lesson.from_today_count === "number" && lesson.from_today_count > 0 && (
          <> · {lesson.from_today_count} {lesson.from_today_count === 1 ? "veio" : "vieram"} dos blocos de hoje</>
        )}
      </p>
      <div className="panel p-7">
        <p className="label">
          {item.from_today ? "Você viu isto hoje — recupere sem olhar" : "Recupere da memória"}
        </p>
        <p className="mt-5 text-2xl font-semibold">{prompt}</p>
        {revealed && (
          <p className="mt-5 border-t border-border pt-5 text-xl font-semibold text-primary">
            {answer}
          </p>
        )}
      </div>
      {error && (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      )}
      <div className="mt-4 flex flex-wrap justify-end gap-2">
        {!revealed ? (
          <Button onClick={() => setRevealed(true)}>Ver resposta</Button>
        ) : (
          [
            { value: "again", label: "De novo" },
            { value: "hard", label: "Difícil" },
            { value: "good", label: "Bom" },
            { value: "easy", label: "Fácil" },
          ].map((option) => (
            <Button
              key={option.value}
              variant={option.value === "good" || option.value === "easy" ? "primary" : "secondary"}
              loading={saving}
              disabled={saving}
              onClick={() => void rate(option.value)}
            >
              {option.label}
            </Button>
          ))
        )}
      </div>
    </div>
  );
}

function DayObjectiveBanner({
  objective,
}: {
  objective: DayLearningObjective;
}) {
  return (
    <div className="mt-6 flex flex-col gap-2 border-y border-border py-4 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6">
      <p className="text-base leading-7 text-text-primary">
        <span className="text-text-secondary">Objetivo: </span>
        <span className="font-semibold">{objective.learner_goal}</span>
      </p>
      <p
        className="shrink-0 text-sm text-text-secondary"
        title={
          objective.status_label !== "Demonstrado"
            ? "Concluir os blocos do dia não significa domínio — o domínio exige evidência e transferência."
            : undefined
        }
      >
        Status: <span className="font-semibold text-text-primary">{objective.status_label}</span>
      </p>
    </div>
  );
}

function MiniTeachingPractice({
  blockId,
  initial,
  languageCode,
}: {
  blockId: string;
  initial: SliceSession | null;
  languageCode: string;
}) {
  const [session, setSession] = useState<SliceSession | null>(initial);
  const [response, setResponse] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (!session) return null;
  if (!session.current_activity) {
    return (
      <div className="panel mb-6 p-5" role="status">
        <h3 className="section-title">Prática de vocabulário concluída</h3>
        <p className="mt-2 text-sm leading-6 text-text-secondary">
          Suas respostas foram registradas. Os itens que precisam de reforço voltarão depois.
        </p>
      </div>
    );
  }
  const activity = session.current_activity;
  const inRemediation =
    session.flow.phase === "needs_remediation" ||
    session.flow.phase === "retrying" ||
    Boolean(session.remediation);
  const locked = Boolean(session.activity_locked) && !inRemediation;
  const acknowledgement = activityIsAcknowledgement(activity);
  const needsResponse = !acknowledgement;

  async function submit() {
    if (busy || (locked && !inRemediation)) return;
    if (needsResponse && !response.trim()) {
      setError(
        activity.type === "multiple_choice"
          ? "Escolha uma alternativa antes de enviar."
          : "Escreva uma resposta antes de continuar.",
      );
      return;
    }
    setBusy(true);
    setError("");
    try {
      const path = inRemediation
        ? `/api/v1/curriculum/block/${blockId}/teaching/retry`
        : `/api/v1/curriculum/block/${blockId}/teaching/answer`;
      const body = inRemediation
        ? {
            remediation_id: session?.remediation?.id,
            student_response: response,
          }
        : {
            student_response: response || "__ack__",
            ...(activity.vocabulary_item_id
              ? { activity_index: session!.flow.activity_cursor }
              : {}),
          };
      const next = await api<SliceSession>(path, { method: "POST", body });
      setSession(next);
      setResponse("");
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "Não foi possível enviar a resposta.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel mb-6 p-5">
      <p className="label">
        Prática do objetivo · {session.flow.phase_label_pt}
      </p>
      <div className="mt-4">
        <TeachingActivityBody
          activity={activity}
          response={response}
          onResponse={setResponse}
          locked={locked}
          languageCode={languageCode}
        />
      </div>
      <TeachingAnswerFeedback
        feedback={session.answer_feedback ?? session.remediation?.answer_feedback}
      />
      {session.remediation && (
        <p className="mt-3 text-sm text-warning">
          {session.remediation.hint_pt ||
            "A tentativa anterior ficou registrada. Responda a nova atividade."}
        </p>
      )}
      {session.mastery?.state === "mastered" && (
        <p className="mt-3 text-sm font-semibold text-primary">Objetivo demonstrado.</p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
      <div className="mt-4">
        <Button
          loading={busy}
          disabled={
            busy ||
            (locked && !inRemediation) ||
            (needsResponse && !response.trim() && inRemediation && !acknowledgement)
          }
          onClick={() => void submit()}
        >
          {acknowledgement
            ? "Continuar"
            : inRemediation
              ? "Tentar novamente"
              : "Enviar tentativa"}
        </Button>
      </div>
    </div>
  );
}

function BlockRunner({
  block,
  missionScenario,
  languageCode,
  onCompleted,
}: {
  block: CurriculumBlock;
  missionScenario?: string;
  languageCode?: string;
  onCompleted: () => void;
}) {
  const [lesson, setLesson] = useState<BlockLesson | null>(null);
  const [teaching, setTeaching] = useState<SliceSession | null>(null);
  const [error, setError] = useState("");
  const [rawError, setRawError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [finishing, setFinishing] = useState(false);
  const grammarGate = (block.mode ?? block.skill) === "grammar";
  const vocabularyBlock = (block.mode ?? block.skill) === "vocabulary";
  const [practiceReady, setPracticeReady] = useState(!grammarGate);

  const start = useCallback(async () => {
    setLoading(true);
    setError("");
    setRawError(null);
    try {
      const payload = await api<StartBlockResponse>(
        `/api/v1/curriculum/block/${block.id}/start`,
        { method: "POST", body: {} },
      );
      setLesson(payload.lesson);
      setTeaching(payload.teaching ?? null);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível abrir este bloco.",
      );
      setRawError(caught);
    } finally {
      setLoading(false);
    }
  }, [block.id]);

  useEffect(() => {
    void start();
  }, [start]);

  async function finish() {
    setFinishing(true);
    setError("");
    try {
      await api<CompleteBlockResponse>(`/api/v1/curriculum/block/${block.id}/complete`, {
        method: "POST",
        body: {},
      });
      onCompleted();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível concluir este bloco.",
      );
    } finally {
      setFinishing(false);
    }
  }

  if (loading) return <Loading label={`Preparando ${block.skill_label}`} />;
  if (error && !lesson) {
    return <ErrorState message={error} retry={() => void start()} error={rawError} />;
  }
  if (!lesson) return null;

  return (
    <div>
      <div className="mb-7">
        <p className="text-sm text-text-secondary">
          <span className="font-semibold text-primary">
            {journeyPhaseLabel(block.phase, block.phase_label)}
          </span>{" "}
          · {block.skill_label} · {block.estimated_minutes} min · {levelShortCode(block.cefr_level)}
        </p>
        <h2 className="mt-2 font-display text-[1.75rem] font-medium leading-tight tracking-[-0.015em]">
          {lesson.title}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{block.topic}</p>
        {block.phase_why && (
          <p className="mt-3 max-w-2xl text-sm leading-6 text-text-secondary">{block.phase_why}</p>
        )}
        {lesson.provider === "mock" && (
          <Note className="mt-3">Gerado em modo mock (IA local)</Note>
        )}
      </div>

      <ThreadBanner lesson={lesson} />

      {teaching?.current_activity && block.skill !== "review" && (
        <MiniTeachingPractice
          blockId={block.id}
          initial={teaching}
          languageCode={
            typeof lesson.language_code === "string" ? lesson.language_code : "en"
          }
        />
      )}

      {block.skill === "review" ? (
        <ReviewQueue lesson={lesson} />
      ) : vocabularyBlock && teaching?.status === "no_vocabulary_due" ? (
        <div className="panel p-6" role="status">
          <h2 className="section-title">Vocabulário em dia</h2>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            Não há itens de vocabulário devidos agora. Eles voltarão no momento adequado.
          </p>
        </div>
      ) : vocabularyBlock && teaching?.current_activity ? null : (
        <LessonContent
          mode={block.mode ?? block.skill}
          lesson={lesson as LessonEnvelope}
          onPracticeReady={grammarGate ? setPracticeReady : undefined}
          enableVocabularyCycle={!vocabularyBlock}
          missionScenario={
            block.skill === "conversation" || block.mode === "conversation" || block.mode === "voice"
              ? missionScenario
              : undefined
          }
          coachLanguageCode={
            block.skill === "conversation" || block.mode === "conversation" || block.mode === "voice"
              ? languageCode
              : undefined
          }
        />
      )}

      {error && (
        <p role="alert" className="mt-5 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="mt-8 flex flex-col items-end gap-2 border-t border-border pt-6">
        {grammarGate && !practiceReady && (
          <p className="text-sm text-text-secondary">
            Termine todas as atividades de gramática antes de abrir o card de compreensão.
          </p>
        )}
        <Button
          loading={finishing}
          disabled={finishing || !practiceReady}
          onClick={() => void finish()}
        >
          Concluir e avançar
        </Button>
      </div>
    </div>
  );
}

export default function CurriculumDayPage() {
  const params = useParams<{ id: string }>();
  const { status, data, error, reload } = useCurriculumDay(params.id);
  const { code: languageCode } = useActiveLanguage();
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null);

  if (status === "loading") return <Loading label="Carregando o dia de estudo" />;
  if (status === "error") return <ErrorState message={error} retry={() => void reload()} />;

  const { day, week, curriculum } = data;
  const mission = deriveDailyMission({
    day,
    weekTheme: week.theme,
    languageName: "",
    level: week.cefr_focus,
  });
  const coach = coachFor(languageCode);
  const current =
    day.blocks.find((block) => block.is_current) ??
    day.blocks.find((block) => block.status === "pending" && !block.locked) ??
    null;
  const active =
    day.blocks.find((block) => block.id === activeBlockId && !block.locked) ?? current;
  const finished = day.blocks.every((block) => block.status === "completed");
  const progressPct =
    day.blocks_total > 0 ? Math.round((day.blocks_completed / day.blocks_total) * 100) : 0;

  return (
    <div className="mx-auto max-w-5xl">
      <header>
        <p className="text-sm text-text-secondary">
          Semana {week.week_number} · {week.theme}
          {week.is_checkpoint && (
            <span className="ml-2 text-xs font-semibold text-[var(--gold-ink)]">Checkpoint</span>
          )}
        </p>
        <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-text-secondary">
          Missão {day.day_number}
        </p>
        <h1 className="mt-2 page-title">{mission.title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-text-secondary">
          {mission.learner_goal}
        </p>
        <p className="mt-2 text-xs text-text-secondary">
          {coach.display_name} acompanha esta missão
          {mission.level ? ` · ${levelShortCode(mission.level) ?? mission.level}` : ""}
          {" · "}
          {day.total_minutes} min
        </p>
        <p className="mt-2 text-sm text-text-secondary">
          Dia {day.day_number}
          {curriculum.duration_days ? ` de ${curriculum.duration_days}` : ""}
          {" · "}
          {day.blocks_completed} de {day.blocks_total} blocos
        </p>
        <div
          className="mt-4 h-1.5 max-w-md rounded-full bg-surface-elevated"
          role="progressbar"
          aria-label="Progresso da missão"
          aria-valuemin={0}
          aria-valuemax={day.blocks_total}
          aria-valuenow={day.blocks_completed}
        >
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </header>

      {day.learning_objective && (
        <DayObjectiveBanner objective={day.learning_objective} />
      )}

      {week.is_checkpoint && finished && (
        <div className="panel mt-6 p-5">
          <p className="text-sm font-semibold text-[var(--gold-ink)]">
            Semana de checkpoint
          </p>
          <p className="mt-1 text-sm text-text-secondary">
            Faça a mini-avaliação para atualizar seu nível e liberar a próxima fase do
            cronograma.
          </p>
          <Link
            href={`/placement-test?curriculum=${curriculum.id}&week=${week.week_number}`}
            className="mt-3 inline-flex text-sm font-semibold text-primary hover:underline"
            onClick={(event) => {
              // Abre o checkpoint via API quando disponível no fluxo do cronograma.
              event.preventDefault();
              void api<{ placement_test_id: string }>(
                `/api/v1/curriculum/${curriculum.id}/checkpoint/${week.week_number}/start`,
                { method: "POST", body: {} },
              )
                .then((result) => {
                  window.location.href = `/placement-test/${result.placement_test_id}`;
                })
                .catch(() => {
                  window.location.href = "/placement-test";
                });
            }}
          >
            Iniciar checkpoint da semana {week.week_number}
          </Link>
        </div>
      )}

      <div className="mt-8 grid gap-10 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <nav aria-label="Caminho do dia" className="lg:sticky lg:top-6 lg:self-start">
          <p className="label mb-3">Sequência do dia</p>
          <ol className="grid gap-1">
            {day.blocks.map((block, index) => {
              const done = block.status === "completed";
              const locked = Boolean(block.locked);
              const selected = active?.id === block.id;
              return (
                <li key={block.id}>
                  <button
                    type="button"
                    disabled={locked}
                    onClick={() => {
                      if (!locked) setActiveBlockId(block.id);
                    }}
                    aria-current={selected ? "step" : undefined}
                    className={`flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left text-sm transition-colors ${
                      selected
                        ? "bg-surface font-semibold text-text-primary shadow-[inset_0_0_0_1px_var(--border)]"
                        : locked
                          ? "cursor-not-allowed text-text-secondary"
                          : "hover:bg-surface-elevated"
                    }`}
                  >
                    <span
                      className={`display-number grid size-7 shrink-0 place-items-center rounded-full text-sm ${
                        done
                          ? "bg-success text-white"
                          : selected
                            ? "bg-primary text-white"
                            : "border border-border bg-background text-text-secondary"
                      }`}
                    >
                      {done ? (
                        <Check className="size-3.5" aria-hidden />
                      ) : locked ? (
                        <Lock className="size-3" aria-hidden />
                      ) : (
                        index + 1
                      )}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className={`block leading-5 ${done ? "text-text-secondary" : ""}`}>
                        {journeyPhaseLabel(block.phase, block.skill_label)}
                      </span>
                      <span className="block text-[.7rem] font-medium text-text-secondary">
                        {block.skill_label}
                      </span>
                    </span>
                    <span className="shrink-0 text-xs font-normal text-text-secondary tabular-nums">
                      {block.estimated_minutes} min
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          {day.thread && <DayThread thread={day.thread} />}
        </nav>

        <div className="min-w-0 max-w-3xl">
          {finished && !activeBlockId ? (
            <div className="panel p-8" role="status">
              <h2 className="text-xl font-semibold">Missão concluída</h2>
              <p className="mt-3 text-sm leading-6 text-text-secondary">
                Você praticou esta sequência. Concluir a missão registra o percurso do dia;
                não equivale a domínio da habilidade.
              </p>
              <ul className="mt-4 grid gap-1 text-sm text-text-secondary">
                {day.blocks.map((block) => (
                  <li key={block.id}>
                    Você praticou {journeyPhaseLabel(block.phase, block.skill_label).toLowerCase()}
                    {" · "}
                    {block.skill_label}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm text-text-secondary">
                {day.blocks_completed} blocos concluídos
              </p>
              {day.thread && day.thread.terms.length > 0 && (
                <p className="mt-2 text-sm leading-6 text-text-secondary">
                  Vocabulário deste dia: {day.thread.terms.map((item) => item.term).join(" · ")}.
                  A revisão espaçada segue o prazo do SRS.
                </p>
              )}
              {day.next_day?.available && (
                <p className="mt-4 text-sm text-text-primary">
                  Amanhã: {day.next_day.topic || day.next_day.theme || `Dia ${day.next_day.day_number}`}
                </p>
              )}
              <div className="mt-6 flex flex-col items-start gap-3">
                {day.next_day?.available && (
                  <Link
                    href={`/cronograma/dia/${day.next_day.id}`}
                    className="inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white hover:bg-[var(--primary-hover)]"
                  >
                    Continuar
                  </Link>
                )}
                <Link
                  href="/cronograma"
                  className="text-sm font-semibold text-text-secondary hover:text-primary"
                >
                  Voltar ao cronograma
                </Link>
              </div>
            </div>
          ) : active ? (
            <BlockRunner
              key={active.id}
              block={active}
              missionScenario={mission.scenario}
              languageCode={languageCode}
              onCompleted={() => {
                setActiveBlockId(null);
                void reload();
              }}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
