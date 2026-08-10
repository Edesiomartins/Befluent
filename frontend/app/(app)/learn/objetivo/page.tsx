"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, RotateCcw } from "lucide-react";
import { TeachingActivityBody, TeachingAnswerFeedback } from "@/components/teaching-activity";
import { Button, ErrorState, Loading } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { SliceSession } from "@/types/teaching";

export default function ObjectiveSlicePage() {
  const [session, setSession] = useState<SliceSession | null>(null);
  const [booting, setBooting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState("");
  const [awaitingResult, setAwaitingResult] = useState(false);

  const restore = useCallback(async () => {
    setBooting(true);
    setError(null);
    try {
      const data = await api<SliceSession>("/api/v1/teaching/slice/en-a1-can-001/active");
      setSession(data);
      setResponse("");
      setAwaitingResult(Boolean(data.activity_locked && !data.remediation));
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
    setResponse("");
    setAwaitingResult(false);
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

  const inRemediation =
    session?.flow.phase === "needs_remediation" ||
    session?.flow.phase === "retrying" ||
    Boolean(session?.remediation);

  const locked =
    Boolean(session?.activity_locked) ||
    awaitingResult ||
    (Boolean(session?.answer_feedback) && !inRemediation);

  async function submit() {
    if (!session || loading || locked) return;
    setLoading(true);
    setAwaitingResult(true);
    setError(null);
    try {
      const needsText = !["listen", "recognition", "matching"].includes(
        session.current_activity?.type ?? "",
      );
      if (needsText && !response.trim()) {
        setError(
          session.current_activity?.type === "multiple_choice"
            ? "Escolha uma alternativa antes de enviar."
            : "Escreva uma resposta antes de continuar.",
        );
        setAwaitingResult(false);
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
    } catch (err) {
      setAwaitingResult(false);
      setError(err instanceof ApiError ? err.message : "Falha ao enviar a tentativa.");
    } finally {
      setLoading(false);
    }
  }

  async function retry() {
    if (!session?.remediation || loading) return;
    setLoading(true);
    setError(null);
    try {
      const actType = session.current_activity?.type ?? "";
      const isAck = ["listen", "recognition", "matching"].includes(actType);
      if (!response.trim() && actType === "multiple_choice") {
        setError("Escolha uma alternativa na nova tentativa.");
        setLoading(false);
        return;
      }
      if (!response.trim() && !isAck) {
        setError("Escreva uma resposta para a nova tentativa.");
        setLoading(false);
        return;
      }
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
      setAwaitingResult(Boolean(data.answer_feedback && !data.remediation));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha no retry.");
    } finally {
      setLoading(false);
    }
  }

  const activity = session?.current_activity ?? null;
  const mastered = session?.mastery?.state === "mastered" || session?.flow.phase === "mastered";
  const feedback = session?.answer_feedback ?? session?.remediation?.answer_feedback;

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
        domínio — só evidência. Cada envio é uma tentativa: não dá para trocar depois.
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
          </div>

          {mastered ? (
            <div className="rounded-2xl border border-primary/30 bg-primary-soft/40 px-5 py-5">
              <p className="text-lg font-semibold text-primary">Objetivo dominado</p>
              <p className="mt-2 text-sm leading-6 text-text-secondary">
                A evidência foi suficiente. Revisaremos depois pela memória universal.
              </p>
              <Button className="mt-4" onClick={start}>
                Recomeçar demonstração
              </Button>
            </div>
          ) : activity ? (
            <>
              <TeachingActivityBody
                activity={activity}
                response={response}
                onResponse={setResponse}
                locked={locked && !inRemediation}
              />

              <TeachingAnswerFeedback feedback={feedback} />

              {session.remediation && (
                <div className="rounded-2xl border border-amber-500/30 bg-amber-50 px-5 py-4 dark:bg-amber-950/20">
                  <p className="font-semibold text-text-primary">Vamos corrigir isto</p>
                  <p className="mt-2 text-sm leading-6 text-text-secondary">
                    {session.remediation.hint_pt ||
                      "A tentativa anterior ficou registrada. Responda a nova atividade abaixo."}
                  </p>
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                {inRemediation ? (
                  <Button
                    onClick={() => void retry()}
                    disabled={
                      loading ||
                      (!response.trim() &&
                        !["listen", "recognition", "matching"].includes(
                          activity.type,
                        ))
                    }
                    loading={loading}
                  >
                    <RotateCcw className="mr-2 size-4" aria-hidden />
                    {["listen", "recognition", "matching"].includes(activity.type)
                      ? "Continuar"
                      : "Tentar novamente"}
                  </Button>
                ) : (
                  <Button
                    onClick={() => void submit()}
                    disabled={loading || locked}
                    loading={loading}
                  >
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
