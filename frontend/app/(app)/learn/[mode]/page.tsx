"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { LessonContent } from "@/components/lesson-modes";
import { Button, ErrorState, Loading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useLesson } from "@/hooks/use-lesson";
import type { LessonEnvelope } from "@/types/lesson";

const meta: Record<string, { title: string }> = {
  guided: { title: "Aula guiada" },
  conversation: { title: "Conversação por texto" },
  voice: { title: "Conversa por voz" },
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
    <div className="flex flex-wrap items-center gap-2">
      <span className="w-fit rounded-md bg-primary-soft px-2.5 py-1.5 text-xs font-semibold text-primary">
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
        <span className="w-fit rounded-md bg-info/10 px-2.5 py-1.5 text-xs font-semibold text-info">
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
      <Link href="/learn" className="text-sm font-medium text-text-secondary hover:text-primary">
        ← Voltar para aprender
      </Link>
      <div className="mt-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="page-title">{lesson?.title ?? fallback.title}</h1>
          {lesson?.objective && <p className="mt-2 text-text-secondary">{lesson.objective}</p>}
        </div>
        {lesson && <LevelBadge lesson={lesson} />}
      </div>
    </header>
  );
}

type DueReview = {
  id: string;
  item_type: string;
  reference_id: string;
  payload: Record<string, unknown>;
  next_review_at: string | null;
};

const REVIEW_RATINGS = [
  { value: "again", label: "De novo" },
  { value: "hard", label: "Difícil" },
  { value: "good", label: "Bom" },
  { value: "easy", label: "Fácil" },
] as const;

function DueReviews() {
  const [items, setItems] = useState<DueReview[] | null>(null);
  const [index, setIndex] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(0);

  useEffect(() => {
    let active = true;
    api<DueReview[]>("/api/v1/reviews/due")
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
  }, []);

  if (items === null) return <Loading label="Carregando revisões" />;
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
  const term = typeof item.payload?.term === "string" ? item.payload.term : null;
  const prompt =
    term ||
    (typeof item.payload?.prompt === "string" ? item.payload.prompt : null) ||
    `${item.item_type} · ${item.reference_id.slice(0, 8)}`;
  const answer =
    (typeof item.payload?.translation_pt === "string" && item.payload.translation_pt) ||
    (typeof item.payload?.answer === "string" && item.payload.answer) ||
    "Revise este item e avalie sua lembrança.";

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
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Recupere da memória
        </p>
        <p className="mt-6 text-2xl font-semibold">{prompt}</p>
        {revealed ? (
          <div className="mt-6 border-t border-border pt-5">
            <p className="text-xl font-semibold text-primary">{answer}</p>
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
        className="mt-7 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
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
    <div>
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
      <div>
        <PageHeader mode={mode} lesson={null} />
        <Assessment />
      </div>
    );
  }
  if (mode === "review") {
    return (
      <div>
        <PageHeader mode={mode} lesson={null} />
        <DueReviews />
      </div>
    );
  }
  return <AdaptiveLesson mode={mode} />;
}
