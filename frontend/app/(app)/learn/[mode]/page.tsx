"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { LessonContent } from "@/components/lesson-modes";
import { AudioPlayer } from "@/components/study";
import { Button, ErrorState, Loading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useLesson } from "@/hooks/use-lesson";
import type { LessonEnvelope } from "@/types/lesson";

const meta: Record<string, { title: string }> = {
  guided: { title: "Aula guiada" },
  conversation: { title: "Conversação por texto" },
  voice: { title: "Conversação" },
  pronunciation: { title: "Pronúncia" },
  vocabulary: { title: "Vocabulário" },
  grammar: { title: "Gramática" },
  listening: { title: "Compreensão auditiva" },
  reading: { title: "Leitura" },
  writing: { title: "Escrita" },
  review: { title: "Revisão" },
  assessment: { title: "Diagnóstico" },
};

const SOURCE_LABELS: Record<string, string> = {
  placement_test: "estimado pelo teste de nivelamento",
  self_declared: "informado por você",
  self_declared_beginner: "informado por você",
  admin: "definido pela equipe",
  imported: "importado",
  pending: "padrão até você fazer o teste",
};

function LevelBadge({ lesson }: { lesson: LessonEnvelope }) {
  const source = SOURCE_LABELS[lesson.level_source] ?? "padrão";
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 sm:justify-end">
      <span className="w-fit text-sm font-medium text-text-secondary">
        Nível {lesson.level} · {source}
      </span>
      {!lesson.level_is_estimated && (
        <Link
          href="/placement-test"
          className="text-xs font-semibold text-primary hover:underline"
        >
          Fazer teste de nível
        </Link>
      )}
      {lesson.provider === "mock" && (
        <span className="note w-fit">
          Gerado em modo mock (IA local)
        </span>
      )}
    </div>
  );
}

function PageHeader({ mode, lesson }: { mode: string; lesson: LessonEnvelope | null }) {
  const fallback = meta[mode];
  return (
    <header className="mb-8">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="page-title">{lesson?.title ?? fallback.title}</h1>
          {lesson?.objective && (
            <p className="mt-3 max-w-2xl leading-7 text-text-secondary">
              <span className="font-semibold text-text-primary">Objetivo: </span>
              {lesson.objective}
            </p>
          )}
        </div>
        {lesson && <LevelBadge lesson={lesson} />}
      </div>
    </header>
  );
}

type ReviewAudioTarget = {
  audio_target_type?: string;
  audio_text?: string;
};

type DueReview = {
  id: string;
  item_type: string;
  reference_id: string;
  payload: Record<string, unknown>;
  next_review_at: string | null;
};

function payloadText(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function reviewAudioTargets(payload: Record<string, unknown>): ReviewAudioTarget[] {
  return Array.isArray(payload.audio_targets)
    ? (payload.audio_targets as ReviewAudioTarget[])
    : [];
}

const REVIEW_RATINGS = [
  { value: "again", label: "De novo" },
  { value: "hard", label: "Difícil" },
  { value: "good", label: "Bom" },
  { value: "easy", label: "Fácil" },
] as const;

function DueReviews() {
  const { code, resolved } = useActiveLanguage();
  const [items, setItems] = useState<DueReview[] | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(0);

  useEffect(() => {
    if (!resolved) return;
    let active = true;
    setItems(null);
    setIndex(0);
    setRevealed(false);
    setDone(0);
    setError("");
    api<DueReview[]>(
      `/api/v1/reviews/due?language_code=${encodeURIComponent(code)}`,
    )
      .then((payload) => {
        if (active) setItems(payload);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar as revisões.",
        );
        setItems([]);
      });
    return () => {
      active = false;
    };
  }, [code, resolved]);

  if (!resolved || items === null) return <Loading label="Carregando revisões" />;
  if (error && items.length === 0) {
    return <ErrorState message={error} retry={() => window.location.reload()} />;
  }
  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl rounded-xl border border-border bg-surface p-8 text-center">
        <h2 className="text-xl font-semibold">Nenhuma revisão pendente</h2>
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          Quando você salvar vocabulário, os itens aparecem aqui no prazo certo.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/learn/vocabulary"
            className="inline-flex min-h-11 items-center rounded-xl bg-primary px-4 text-sm font-semibold text-white"
          >
            Praticar vocabulário
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex min-h-11 items-center rounded-xl border border-border px-4 text-sm font-semibold"
          >
            Voltar ao painel
          </Link>
        </div>
      </div>
    );
  }

  if (index >= items.length) {
    return (
      <div className="mx-auto max-w-2xl rounded-xl border border-border bg-surface p-8 text-center">
        <h2 className="text-xl font-semibold">Revisão concluída</h2>
        <p className="mt-3 text-sm text-text-secondary">
          Você respondeu {done} {done === 1 ? "item" : "itens"}. O agendamento foi atualizado.
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-flex min-h-11 items-center rounded-xl bg-primary px-4 text-sm font-semibold text-white"
        >
          Ir ao painel
        </Link>
      </div>
    );
  }

  const item = items[index];
  const term = payloadText(item.payload, "term");
  const prompt =
    term ||
    payloadText(item.payload, "prompt") ||
    `${item.item_type} · ${item.reference_id.slice(0, 8)}`;
  const answer =
    payloadText(item.payload, "translation_pt") ||
    payloadText(item.payload, "answer") ||
    "Revise este item e avalie sua lembrança.";
  const example = payloadText(item.payload, "example");
  const exampleTranslation = payloadText(item.payload, "example_translation_pt");
  const lexical = item.payload.review_mode === "lexical_v2";
  const audioTargets = reviewAudioTargets(item.payload);
  const termAudio = audioTargets.find((target) => target.audio_target_type === "vocabulary_item");
  const exampleAudio = audioTargets.find(
    (target) => target.audio_target_type === "example_sentence",
  );

  async function rate(rating: string) {
    setSaving(true);
    setError("");
    try {
      await api(`/api/v1/reviews/${item.id}/answer`, {
        method: "POST",
        body: { rating },
      });
      setDone((value) => value + 1);
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
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex justify-between text-sm text-text-secondary">
        <span>
          {items.length - index}{" "}
          {items.length - index === 1 ? "item restante" : "itens restantes"}
        </span>
        <span>{item.item_type}</span>
      </div>
      <div className="panel p-8">
        <p className="label">
          Recupere da memória
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <p className="text-2xl font-semibold">{prompt}</p>
          {lexical && termAudio?.audio_text && (
            <AudioPlayer
              variant="compact"
              accessibleName={`Ouvir expressão ${term ?? ""}`.trim()}
              text={termAudio.audio_text}
              languageCode={code}
            />
          )}
        </div>
        {revealed ? (
          <div className="mt-6 border-t border-border pt-5 space-y-3">
            <p className="text-xl font-semibold text-primary">{answer}</p>
            {example && (
              <div className="flex flex-wrap items-center gap-3">
                {exampleAudio?.audio_text && (
                  <AudioPlayer
                    variant="compact"
                    accessibleName="Ouvir frase de exemplo"
                    text={exampleAudio.audio_text}
                    languageCode={code}
                  />
                )}
                <p className="text-lg italic text-text-secondary">“{example}”</p>
              </div>
            )}
            {exampleTranslation && (
              <p className="text-sm text-text-secondary">{exampleTranslation}</p>
            )}
          </div>
        ) : (
          <p className="mt-4 text-sm text-text-secondary">
            Pense na resposta e revele quando estiver pronto.
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
          REVIEW_RATINGS.map((option) => (
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

function Assessment() {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold tracking-tight">Diagnóstico de nível</h2>
      <p className="mt-3 leading-7 text-text-secondary">
        O diagnóstico agora é o teste de nivelamento completo, com resultado por
        competência, confiança da estimativa e recomendações de estudo.
      </p>
      <Link
        href="/placement-test"
        className="mt-7 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white hover:bg-[var(--primary-hover)]"
      >
        Ir para o teste de nivelamento
      </Link>
    </div>
  );
}

function AdaptiveLesson({ mode }: { mode: string }) {
  const { code } = useActiveLanguage();
  const { status, lesson, error, rawError, reload } = useLesson(mode, code);
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader mode={mode} lesson={lesson} />
      {status === "loading" && <Loading label={`Preparando ${meta[mode].title}`} />}
      {status === "error" && (
        <ErrorState message={error ?? undefined} retry={() => void reload()} error={rawError} />
      )}
      {status === "ready" && lesson && <LessonContent mode={mode} lesson={lesson} />}
    </div>
  );
}

export default function StudyModePage() {
  const params = useParams<{ mode: string }>();
  const mode = params.mode;
  if (!meta[mode]) {
    // `notFound()` lança em produção; o return explícito evita seguir com um
    // modo inexistente caso isso mude.
    notFound();
    return null;
  }
  if (mode === "assessment") {
    return (
      <div className="mx-auto max-w-3xl">
        <PageHeader mode={mode} lesson={null} />
        <Assessment />
      </div>
    );
  }
  if (mode === "review") {
    return (
      <div className="mx-auto max-w-3xl">
        <PageHeader mode={mode} lesson={null} />
        <DueReviews />
      </div>
    );
  }
  return <AdaptiveLesson mode={mode} />;
}
