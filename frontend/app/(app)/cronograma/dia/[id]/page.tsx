"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Check, Circle } from "lucide-react";
import { LessonContent } from "@/components/lesson-modes";
import { Button, ErrorState, Loading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { levelShortCode } from "@/lib/levels";
import { useCurriculumDay } from "@/hooks/use-curriculum";
import type { LessonEnvelope } from "@/types/lesson";
import type {
  BlockLesson,
  CompleteBlockResponse,
  CurriculumBlock,
  StartBlockResponse,
} from "@/types/curriculum";

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
        <h2 className="section-title">Nada vencido na fila</h2>
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          {lesson.empty_notice ??
            "Nenhum item vencido hoje. Salve vocabulário para alimentar a revisão."}
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
      </p>
      <div className="panel p-7">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Recupere da memória
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

function BlockRunner({
  block,
  onCompleted,
}: {
  block: CurriculumBlock;
  onCompleted: () => void;
}) {
  const [lesson, setLesson] = useState<BlockLesson | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [finishing, setFinishing] = useState(false);

  const start = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await api<StartBlockResponse>(
        `/api/v1/curriculum/block/${block.id}/start`,
        { method: "POST", body: {} },
      );
      setLesson(payload.lesson);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível abrir este bloco.",
      );
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
  if (error && !lesson) return <ErrorState message={error} retry={() => void start()} />;
  if (!lesson) return null;

  return (
    <div>
      <div className="mb-6 border-l-2 border-primary pl-4">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-primary">
          {block.skill_label} · {block.estimated_minutes} min ·{" "}
          {levelShortCode(block.cefr_level)}
        </p>
        <h2 className="mt-1.5 text-xl font-semibold tracking-tight">{lesson.title}</h2>
        <p className="mt-1 text-sm text-text-secondary">{block.topic}</p>
        {lesson.provider === "mock" && (
          <span className="mt-3 inline-flex rounded-md bg-info/10 px-2.5 py-1.5 text-xs font-semibold text-info">
            Gerado em modo mock (IA local)
          </span>
        )}
      </div>

      {block.skill === "review" ? (
        <ReviewQueue lesson={lesson} />
      ) : (
        <LessonContent mode={block.mode ?? block.skill} lesson={lesson as LessonEnvelope} />
      )}

      {error && (
        <p role="alert" className="mt-5 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="mt-8 flex justify-end border-t border-border pt-6">
        <Button loading={finishing} disabled={finishing} onClick={() => void finish()}>
          Concluir bloco
        </Button>
      </div>
    </div>
  );
}

export default function CurriculumDayPage() {
  const params = useParams<{ id: string }>();
  const { status, data, error, reload } = useCurriculumDay(params.id);
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null);

  if (status === "loading") return <Loading label="Carregando o dia de estudo" />;
  if (status === "error") return <ErrorState message={error} retry={() => void reload()} />;

  const { day, week } = data;
  const pending = day.blocks.filter((block) => block.status === "pending");
  // Sem escolha explícita, o dia continua do primeiro bloco em aberto.
  const active =
    day.blocks.find((block) => block.id === activeBlockId) ?? pending[0] ?? null;
  const finished = pending.length === 0;

  return (
    <div>
      <Link
        href="/cronograma"
        className="text-sm font-medium text-text-secondary hover:text-primary"
      >
        ← Voltar para o cronograma
      </Link>

      <header className="mt-5">
        <p className="text-sm font-semibold text-primary">
          Semana {week.week_number} · {week.theme}
          {week.is_checkpoint && (
            <span className="ml-2 rounded-md bg-[var(--gold-soft)] px-2 py-0.5 text-xs font-semibold text-[var(--gold-ink)]">
              Checkpoint
            </span>
          )}
        </p>
        <h1 className="mt-2 page-title">Dia {day.day_number}</h1>
        <p className="mt-2 text-text-secondary">
          {day.blocks_completed} de {day.blocks_total} blocos concluídos ·{" "}
          {day.total_minutes} min estimados
        </p>
      </header>

      <div className="mt-6 grid gap-8 lg:grid-cols-[16rem_1fr]">
        {/* Sequência do dia */}
        <nav aria-label="Blocos do dia">
          <ol className="grid gap-1">
            {day.blocks.map((block) => {
              const done = block.status === "completed";
              const current = active?.id === block.id;
              return (
                <li key={block.id}>
                  <button
                    type="button"
                    onClick={() => setActiveBlockId(block.id)}
                    aria-current={current ? "step" : undefined}
                    className={`flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition ${
                      current
                        ? "bg-primary-soft font-semibold text-primary"
                        : "hover:bg-surface-elevated"
                    }`}
                  >
                    {done ? (
                      <Check className="size-4 shrink-0 text-success" aria-hidden />
                    ) : (
                      <Circle className="size-4 shrink-0 text-border" aria-hidden />
                    )}
                    <span className={`min-w-0 flex-1 truncate ${done ? "line-through" : ""}`}>
                      {block.skill_label}
                    </span>
                    <span className="shrink-0 text-xs text-text-secondary tabular-nums">
                      {block.estimated_minutes}min
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>

        {/* Bloco em execução */}
        <div>
          {finished && !activeBlockId ? (
            <div className="panel p-8 text-center" role="status">
              <h2 className="text-xl font-semibold">Dia concluído</h2>
              <p className="mt-3 text-sm leading-6 text-text-secondary">
                Você completou os {day.blocks_total} blocos deste dia.
              </p>
              <Link
                href="/cronograma"
                className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
              >
                Voltar ao cronograma
              </Link>
            </div>
          ) : active ? (
            <BlockRunner
              key={active.id}
              block={active}
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
