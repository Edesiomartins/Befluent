"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, RotateCcw } from "lucide-react";
import { Button, ErrorState, Loading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { SliceSession, TeachingActivity } from "@/types/teaching";

function ActivityBody({
  activity,
  response,
  onResponse,
}: {
  activity: TeachingActivity;
  response: string;
  onResponse: (value: string) => void;
}) {
  if (activity.type === "listen" || activity.type === "recognition") {
    const lines = activity.models ?? activity.examples ?? [];
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        {activity.title_pt && (
          <p className="text-lg font-semibold text-text-primary">{activity.title_pt}</p>
        )}
        {activity.can_do && (
          <p className="rounded-xl bg-surface-elevated px-4 py-3 text-sm leading-6 text-text-primary">
            {activity.can_do}
          </p>
        )}
        {lines.length > 0 && (
          <ul className="space-y-2">
            {lines.map((line) => (
              <li
                key={line}
                className="rounded-xl border border-border bg-surface px-4 py-3 font-medium text-text-primary"
              >
                {line}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (activity.type === "multiple_choice") {
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        <p className="font-medium text-text-primary">{activity.prompt}</p>
        <div className="grid gap-2">
          {(activity.options ?? []).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onResponse(option)}
              className={`rounded-xl border px-4 py-3 text-left text-sm font-semibold transition ${
                response === option
                  ? "border-primary bg-primary-soft text-primary"
                  : "border-border bg-surface text-text-primary hover:border-primary/40"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (activity.type === "word_order") {
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        <p className="text-sm text-text-secondary">
          Palavras: {(activity.tokens ?? []).join(" · ")}
        </p>
        <textarea
          value={response}
          onChange={(event) => onResponse(event.target.value)}
          rows={3}
          className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none ring-primary focus:ring-2"
          placeholder="Escreva a frase na ordem correta"
        />
      </div>
    );
  }

  if (activity.type === "matching") {
    return (
      <div className="space-y-4">
        <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
        <ul className="space-y-2">
          {(activity.pairs ?? []).map((pair) => (
            <li key={pair.term} className="rounded-xl border border-border px-4 py-3">
              <span className="font-semibold text-text-primary">{pair.term}</span>
              <span className="mt-1 block text-sm text-text-secondary">{pair.hint_pt}</span>
            </li>
          ))}
        </ul>
        <p className="text-sm text-text-secondary">
          Leia os pares e continue quando estiver pronto.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="leading-7 text-text-secondary">{activity.prompt_pt}</p>
      {activity.prompt && (
        <p className="text-lg font-semibold text-text-primary">{activity.prompt}</p>
      )}
      {activity.scaffold_pt && (
        <p className="rounded-xl bg-surface-elevated px-4 py-3 text-sm text-text-secondary">
          Apoio: {activity.scaffold_pt}
        </p>
      )}
      {activity.type !== "fill_gap" && activity.canonical_answer && (
        <p className="text-xs text-text-secondary">Modelo de referência disponível após tentativa.</p>
      )}
      {activity.type === "fill_gap" && (
        <p className="font-medium text-text-primary">{activity.prompt}</p>
      )}
      <textarea
        value={response}
        onChange={(event) => onResponse(event.target.value)}
        rows={4}
        className="w-full rounded-xl border border-border bg-surface px-4 py-3 text-text-primary outline-none ring-primary focus:ring-2"
        placeholder="Sua resposta"
      />
    </div>
  );
}

export default function ObjectiveSlicePage() {
  const [session, setSession] = useState<SliceSession | null>(null);
  const [booting, setBooting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const restore = useCallback(async () => {
    setBooting(true);
    setError(null);
    try {
      const data = await api<SliceSession>("/api/v1/teaching/slice/en-a1-can-001/active");
      setSession(data);
      if (data.remediation) {
        setFeedback(data.remediation.hint_pt ?? "Vamos corrigir isto.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setSession(null);
      } else {
        setError(
          err instanceof ApiError ? err.message : "Não foi possível restaurar o objetivo.",
        );
      }
    } finally {
      setBooting(false);
    }
  }, []);

  useEffect(() => {
    void restore();
  }, [restore]);

  const start = useCallback(async () => {
    setLoading(true);
    setError(null);
    setFeedback(null);
    setResponse("");
    try {
      const data = await api<SliceSession>("/api/v1/teaching/slice/en-a1-can-001/start", {
        method: "POST",
        body: {},
      });
      setSession(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível iniciar o objetivo.");
    } finally {
      setLoading(false);
    }
  }, []);

  async function submit() {
    if (!session) return;
    setLoading(true);
    setError(null);
    try {
      const needsText = !["listen", "recognition", "matching"].includes(
        session.current_activity?.type ?? "",
      );
      if (needsText && !response.trim() && session.current_activity?.type !== "multiple_choice") {
        setError("Escreva uma resposta antes de continuar.");
        setLoading(false);
        return;
      }
      const data = await api<SliceSession>(
        `/api/v1/teaching/slice/flows/${session.flow.id}/answer`,
        {
          method: "POST",
          body: { student_response: response },
        },
      );
      setSession(data);
      setResponse("");
      if (data.remediation) {
        setFeedback(data.remediation.hint_pt ?? "Vamos corrigir isto.");
      } else if (data.attempt?.result === "correct") {
        setFeedback("Boa — evidência registrada.");
      } else {
        setFeedback(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao enviar a tentativa.");
    } finally {
      setLoading(false);
    }
  }

  async function retry() {
    if (!session?.remediation) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api<SliceSession>(
        `/api/v1/teaching/slice/flows/${session.flow.id}/retry`,
        {
          method: "POST",
          body: {
            remediation_id: session.remediation.id,
            student_response: response,
          },
        },
      );
      setSession(data);
      setResponse("");
      setFeedback(
        data.attempt?.result === "correct"
          ? "Erro reparado. Continuamos."
          : "Ainda não — tente de novo com o contraste.",
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha no retry.");
    } finally {
      setLoading(false);
    }
  }

  const activity = session?.current_activity ?? null;
  const mastered = session?.mastery?.state === "mastered" || session?.flow.phase === "mastered";

  if (booting) {
    return (
      <div className="mx-auto max-w-2xl">
        <Link
          href="/learn"
          className="inline-flex items-center gap-2 text-sm font-semibold text-text-secondary hover:text-primary"
        >
          <ArrowLeft className="size-4" aria-hidden />
          Voltar à prática
        </Link>
        <div className="mt-10">
          <Loading label="Restaurando o objetivo…" />
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/learn"
        className="inline-flex items-center gap-2 text-sm font-semibold text-text-secondary hover:text-primary"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Voltar à prática
      </Link>

      <p className="mt-6 text-sm font-semibold text-primary">Teaching Engine</p>
      <h1 className="mt-2 page-title">Objetivo EN-A1-CAN-001</h1>
      <p className="mt-3 leading-7 text-text-secondary">
        Apresentar-se e trocar informações pessoais básicas. Conclusão de tela não conta como
        domínio — só evidência.
      </p>

      {!session && (
        <div className="mt-8">
          <Button onClick={start} disabled={loading}>
            Começar objetivo
          </Button>
        </div>
      )}

      {loading && !session && <Loading label="Preparando o fluxo…" />}
      {error && (
        <div className="mt-6">
          <ErrorState message={error} />
        </div>
      )}
      {session && (
        <p className="mt-4 text-xs text-text-secondary">
          Estado mantido pelo servidor (TeachingFlowSession). Atualizar a página restaura fase,
          atividade e remediação — sem reiniciar o objetivo.
        </p>
      )}

      {session && (
        <div className="mt-8 space-y-6">
          <div className="rounded-2xl border border-border bg-surface px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
              Estado pedagógico
            </p>
            <p className="mt-2 text-lg font-semibold text-text-primary">
              {session.flow.phase_label_pt}
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              Domínio: {session.progress_state}
              {session.objective.can_do ? ` · ${session.objective.can_do}` : ""}
            </p>
            <p className="mt-2 text-xs text-text-secondary">
              Passo {Math.min(session.flow.activity_cursor + 1, session.activities_total)} de{" "}
              {session.activities_total}
            </p>
          </div>

          {mastered ? (
            <div className="rounded-2xl border border-primary/30 bg-primary-soft/40 px-5 py-5">
              <p className="text-lg font-semibold text-primary">Objetivo dominado</p>
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                A evidência foi suficiente. Revisaremos depois pela memória universal.
              </p>
              {(session.mastery?.reasons ?? []).map((reason) => (
                <p key={reason} className="mt-2 text-sm text-text-secondary">
                  {reason}
                </p>
              ))}
              <Button className="mt-4" onClick={start}>
                Recomeçar demonstração
              </Button>
            </div>
          ) : activity ? (
            <>
              <ActivityBody activity={activity} response={response} onResponse={setResponse} />

              {session.remediation && (
                <div className="rounded-2xl border border-amber-500/30 bg-amber-50 px-5 py-4 dark:bg-amber-950/20">
                  <p className="font-semibold text-text-primary">Vamos corrigir isto</p>
                  <p className="mt-2 text-sm leading-6 text-text-secondary">
                    {session.remediation.explanation}
                  </p>
                  {session.remediation.contrast && (
                    <div className="mt-3 grid gap-2 text-sm">
                      <p>
                        <span className="font-semibold">Sua resposta:</span>{" "}
                        {session.remediation.contrast.incorrect}
                      </p>
                      <p>
                        <span className="font-semibold">Modelo:</span>{" "}
                        {session.remediation.contrast.correct}
                      </p>
                    </div>
                  )}
                  <p className="mt-3 text-sm text-text-secondary">{session.remediation.hint_pt}</p>
                </div>
              )}

              {feedback && !session.remediation && (
                <p className="text-sm font-medium text-primary">{feedback}</p>
              )}

              <div className="flex flex-wrap gap-3">
                {session.flow.phase === "needs_remediation" || session.remediation ? (
                  <Button onClick={retry} disabled={loading || !response.trim()}>
                    <RotateCcw className="mr-2 size-4" aria-hidden />
                    Tentar novamente
                  </Button>
                ) : (
                  <Button onClick={submit} disabled={loading}>
                    {["listen", "recognition", "matching"].includes(activity.type)
                      ? "Continuar"
                      : "Enviar tentativa"}
                  </Button>
                )}
              </div>
            </>
          ) : (
            <p className="text-sm text-text-secondary">Sem atividade atual neste fluxo.</p>
          )}
        </div>
      )}
    </div>
  );
}
