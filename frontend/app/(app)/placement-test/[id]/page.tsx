"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, ErrorState, Loading } from "@/components/ui";
import type { NextItemResponse, PlacementItem, PlacementProgress } from "@/types/placement";

function AudioPrompt({ script, languageCode }: { script: string; languageCode: string }) {
  const [playing, setPlaying] = useState(false);
  const [unsupported, setUnsupported] = useState(false);

  const speak = useCallback(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setUnsupported(true);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(script);
    utterance.lang = languageCode === "zh-CN" ? "zh-CN" : languageCode;
    utterance.rate = 0.95;
    utterance.onend = () => setPlaying(false);
    window.speechSynthesis.speak(utterance);
    setPlaying(true);
  }, [script, languageCode]);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return (
    <div className="rounded-xl border border-border bg-[var(--surface-soft)] p-4">
      <Button variant="secondary" onClick={speak} type="button">
        {playing ? "Reproduzindo…" : "Ouvir áudio"}
      </Button>
      <p className="mt-2 text-sm text-text-secondary">
        Você pode ouvir quantas vezes precisar.
      </p>
      {unsupported && (
        <p role="alert" className="mt-2 text-sm text-danger">
          Seu navegador não reproduz o áudio desta atividade. Você pode pular esta questão.
        </p>
      )}
    </div>
  );
}

export default function PlacementTestRunnerPage() {
  const params = useParams<{ id: string }>();
  const testId = params.id;
  const router = useRouter();

  const [item, setItem] = useState<PlacementItem | null>(null);
  const [stage, setStage] = useState<NextItemResponse["stage"]>("objective");
  const [progress, setProgress] = useState<PlacementProgress | null>(null);
  const [languageCode, setLanguageCode] = useState("en");
  const [choice, setChoice] = useState("");
  const [writingText, setWritingText] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const shownAt = useRef<number>(Date.now());

  const loadNext = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const payload = await api<NextItemResponse>(
        `/api/v1/placement-tests/${testId}/next-item`,
        { method: "POST" },
      );
      setItem(payload.item);
      setStage(payload.stage);
      setProgress(payload.progress);
      setChoice("");
      setWritingText("");
      shownAt.current = Date.now();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível carregar a próxima atividade.",
      );
    } finally {
      setLoading(false);
    }
  }, [testId]);

  useEffect(() => {
    let active = true;
    api<{ language_code: string }>(`/api/v1/placement-tests/${testId}`)
      .then((test) => {
        if (active) setLanguageCode(test.language_code);
      })
      .catch(() => undefined);
    void loadNext();
    return () => {
      active = false;
    };
  }, [testId, loadNext]);

  async function submitObjective() {
    if (!item || !choice) return;
    setSubmitting(true);
    setError("");
    try {
      await api(`/api/v1/placement-tests/${testId}/answers`, {
        method: "POST",
        body: {
          item_id: item.id,
          answer: choice,
          response_time_ms: Date.now() - shownAt.current,
        },
      });
      await loadNext();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível salvar sua resposta.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function submitWriting() {
    if (!item || !writingText.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      await api(`/api/v1/placement-tests/${testId}/writing`, {
        method: "POST",
        body: {
          item_id: item.id,
          text: writingText.trim(),
          response_time_ms: Date.now() - shownAt.current,
        },
      });
      await loadNext();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível enviar sua produção escrita.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function complete() {
    setSubmitting(true);
    setError("");
    try {
      await api(`/api/v1/placement-tests/${testId}/complete`, { method: "POST" });
      router.replace(`/placement-test/${testId}/resultado`);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível concluir o teste.",
      );
      setSubmitting(false);
    }
  }

  const answered = progress?.answered ?? 0;
  const target = progress?.target ?? 20;
  const percent = Math.min(Math.round((answered / target) * 100), 100);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-sm font-semibold text-primary">Teste de nivelamento</p>
        <p className="text-sm text-text-secondary">
          Atividade {Math.min(answered + 1, target)} de aproximadamente {target}
        </p>
      </div>

      <div
        className="mt-3 h-2.5 overflow-hidden rounded-full bg-surface-elevated"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progresso do teste"
      >
        <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent}%` }} />
      </div>

      <div aria-live="polite" className="mt-7">
        {loading ? (
          <Loading label="Carregando atividade" />
        ) : error && !item ? (
          <ErrorState message={error} retry={() => void loadNext()} />
        ) : stage === "ready_to_complete" || !item ? (
          <section className="panel p-6">
            <h1 className="section-title">Tudo pronto</h1>
            <p className="mt-2 text-sm leading-6 text-text-secondary">
              Você respondeu atividades suficientes para uma estimativa. Vamos calcular
              seu nível.
            </p>
            {error && (
              <p role="alert" className="mt-4 text-sm text-danger">
                {error}
              </p>
            )}
            <Button className="mt-6" onClick={complete} loading={submitting} disabled={submitting}>
              Ver meu resultado
            </Button>
          </section>
        ) : stage === "writing" ? (
          <section className="panel p-6">
            <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
              {item.skill_label}
            </p>
            <h1 className="mt-3 text-lg font-semibold leading-7">{item.prompt}</h1>
            {item.instructions && (
              <p className="mt-2 text-sm text-text-secondary">{item.instructions}</p>
            )}
            <div className="mt-5 grid gap-2">
              <label className="text-sm font-medium" htmlFor="writing-answer">
                Sua resposta
              </label>
              <textarea
                id="writing-answer"
                rows={8}
                value={writingText}
                onChange={(event) => setWritingText(event.target.value)}
                maxLength={4000}
                aria-describedby="writing-counter"
                className="rounded-xl border-2 border-border bg-surface p-3.5 text-sm leading-6"
                placeholder="Escreva aqui…"
              />
              <span id="writing-counter" className="text-sm text-text-secondary">
                {writingText.trim().length} caracteres
              </span>
            </div>
            {error && (
              <p role="alert" className="mt-4 text-sm text-danger">
                {error}
              </p>
            )}
            <Button
              className="mt-5"
              onClick={submitWriting}
              loading={submitting}
              disabled={submitting || !writingText.trim()}
            >
              Enviar e continuar
            </Button>
          </section>
        ) : (
          <section className="panel p-6">
            <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
              {item.skill_label}
            </p>

            {item.audio_script && (
              <div className="mt-4">
                <AudioPrompt script={item.audio_script} languageCode={languageCode} />
              </div>
            )}

            {item.passage && (
              <div className="mt-4 rounded-xl border border-border bg-[var(--surface-soft)] p-4 text-sm leading-7">
                {item.passage}
              </div>
            )}

            <fieldset className="mt-5">
              <legend className="text-lg font-semibold leading-7">{item.prompt}</legend>
              {item.instructions && (
                <p className="mt-2 text-sm text-text-secondary">{item.instructions}</p>
              )}
              <div className="mt-4 grid gap-2">
                {item.options.map((option) => (
                  <label
                    key={option}
                    className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 p-4 text-sm transition ${
                      choice === option
                        ? "border-primary bg-primary-soft font-semibold text-primary"
                        : "border-border bg-surface hover:border-primary/40"
                    }`}
                  >
                    <input
                      type="radio"
                      name="answer"
                      className="sr-only"
                      value={option}
                      checked={choice === option}
                      onChange={() => setChoice(option)}
                    />
                    <span
                      aria-hidden
                      className={`grid size-5 shrink-0 place-items-center rounded-full border-2 ${
                        choice === option ? "border-primary" : "border-border"
                      }`}
                    >
                      {choice === option && <span className="size-2.5 rounded-full bg-primary" />}
                    </span>
                    {option}
                  </label>
                ))}
              </div>
            </fieldset>

            {error && (
              <p role="alert" className="mt-4 text-sm text-danger">
                {error}
              </p>
            )}

            <Button
              className="mt-6"
              onClick={submitObjective}
              loading={submitting}
              disabled={submitting || !choice}
            >
              Continuar
            </Button>
          </section>
        )}
      </div>

      <p className="mt-6 text-center text-sm text-text-secondary">
        Suas respostas são salvas automaticamente. Você pode sair e retomar depois.
      </p>
    </div>
  );
}
