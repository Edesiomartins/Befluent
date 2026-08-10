"use client";

/**
 * Speech Coach V1 — feedback de inteligibilidade (não pronúncia %).
 *
 * Fluxo: TARGET → LISTEN → RECORD → STT → ALIGN → FEEDBACK → REPAIR → RETRY
 */

import { useCallback, useEffect, useState } from "react";
import { Check, Mic, Volume2, X } from "lucide-react";
import { AudioPlayer, Recorder, type TranscriptResult } from "@/components/study";
import { Button } from "@/components/ui";
import { api, ApiError } from "@/lib/api";

export type AlignmentOp = { role: "match" | "miss" | "extra"; token: string };

export type CoachFeedbackPoint = {
  kind: string;
  label_pt: string;
  token: string;
};

export type SpeechCoachResult = {
  status: string;
  is_phonetic_score: boolean;
  pedagogical_error: boolean;
  success: boolean;
  transcript: string;
  normalized_target: string;
  normalized_transcript: string;
  alignment_sequence: AlignmentOp[];
  feedback: {
    summary_pt: string;
    points: CoachFeedbackPoint[];
    metric_name: string;
    metric_label_pt: string;
    coverage: number | null;
  };
  repair: {
    action: string;
    label_pt: string;
    level: number;
    allow_continue: boolean;
    practice_chunk: string | null;
  };
  practice_chunk: string | null;
  attempt_number: number;
  te_evidence?: { attempt_id: string; evidence_type: string } | null;
};

type SessionAttempt = {
  number: number;
  transcript: string;
  success: boolean;
  summary: string;
};

type Phase =
  | "ready"
  | "recording"
  | "processing"
  | "analyzing"
  | "feedback"
  | "chunk_practice";

function AlignmentDiff({
  sequence,
  view,
}: {
  sequence: AlignmentOp[];
  view: "target" | "transcript";
}) {
  const ops =
    view === "target"
      ? sequence.filter((op) => op.role !== "extra")
      : sequence.filter((op) => op.role !== "miss");

  if (!ops.length) {
    return <p className="text-sm text-text-secondary">—</p>;
  }

  return (
    <p className="flex flex-wrap gap-1.5 text-base leading-8" aria-live="polite">
      {ops.map((op, index) => {
        const key = `${op.role}-${op.token}-${index}`;
        if (op.role === "match") {
          return (
            <span
              key={key}
              className="inline-flex items-center gap-1 rounded-md bg-success/10 px-1.5 font-medium text-text-primary"
            >
              <Check className="size-3.5 text-success" aria-hidden />
              <span className="sr-only">Identificado: </span>
              {op.token}
            </span>
          );
        }
        if (op.role === "miss") {
          return (
            <span
              key={key}
              className="inline-flex items-center gap-1 rounded-md bg-danger/10 px-1.5 font-medium text-text-primary"
            >
              <X className="size-3.5 text-danger" aria-hidden />
              <span className="sr-only">Não identificado: </span>
              {op.token}
            </span>
          );
        }
        return (
          <span
            key={key}
            className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-1.5 font-medium text-text-primary"
          >
            <span aria-hidden>+</span>
            <span className="sr-only">Palavra a mais: </span>
            {op.token}
          </span>
        );
      })}
    </p>
  );
}

export function SpeechCoach({
  targetText,
  translation,
  languageCode,
  transferPrompt,
  onSuccess,
  onContinue,
}: {
  targetText: string;
  translation?: string;
  languageCode: string;
  /** Após sucesso: pequena produção (imitação → produção). */
  transferPrompt?: string;
  onSuccess?: () => void;
  onContinue?: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("ready");
  const [result, setResult] = useState<SpeechCoachResult | null>(null);
  const [error, setError] = useState("");
  const [attempts, setAttempts] = useState<SessionAttempt[]>([]);
  const [previousMissed, setPreviousMissed] = useState<string[]>([]);
  const [showTransfer, setShowTransfer] = useState(false);
  const [chunkMode, setChunkMode] = useState(false);

  const attemptNumber = attempts.length + 1;

  const analyze = useCallback(
    async (transcript: string, provider?: string | null) => {
      setPhase("analyzing");
      setError("");
      try {
        const data = await api<SpeechCoachResult>("/api/v1/teaching/speech-coach", {
          method: "POST",
          body: {
            target_text: targetText,
            transcript,
            provider: provider ?? null,
            attempt_number: attemptNumber,
            previous_missed: previousMissed,
            mode: "repetition",
            language_code: languageCode,
            record_evidence: false,
          },
        });
        setResult(data);
        setAttempts((prev) => [
          ...prev,
          {
            number: data.attempt_number,
            transcript: data.transcript || "(vazio)",
            success: data.success,
            summary: data.feedback.summary_pt,
          },
        ]);
        const missed = (data.alignment_sequence || [])
          .filter((op) => op.role === "miss")
          .map((op) => op.token);
        setPreviousMissed(missed);
        if (data.repair.action === "practice_chunk" && data.practice_chunk) {
          setChunkMode(true);
          setPhase("chunk_practice");
        } else {
          setChunkMode(false);
          setPhase("feedback");
        }
        if (data.success) {
          setShowTransfer(Boolean(transferPrompt));
          onSuccess?.();
        }
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível analisar a fala. Tente gravar de novo.",
        );
        setPhase("ready");
      }
    },
    [
      attemptNumber,
      languageCode,
      onSuccess,
      previousMissed,
      targetText,
      transferPrompt,
    ],
  );

  async function onTranscript(text: string, meta?: TranscriptResult) {
    const trimmed = (text || "").trim();
    if (!trimmed) {
      // Silêncio / vazio: issue técnica, não erro pedagógico silencioso no TE.
      await analyze("", meta?.provider);
      return;
    }
    await analyze(trimmed, meta?.provider);
  }

  function resetForRetry() {
    setResult(null);
    setError("");
    setPhase("ready");
  }

  // Descarta áudio da sessão ao trocar de frase-alvo (privacy: sem cache global).
  useEffect(() => {
    setResult(null);
    setAttempts([]);
    setPreviousMissed([]);
    setShowTransfer(false);
    setChunkMode(false);
    setPhase("ready");
    setError("");
  }, [targetText]);

  const phaseLabel: Record<Phase, string> = {
    ready: "Pronto para ouvir e gravar",
    recording: "Gravando…",
    processing: "Processando…",
    analyzing: "Analisando inteligibilidade…",
    feedback: "Feedback",
    chunk_practice: "Praticar trecho",
  };

  const practiceText = result?.practice_chunk || targetText;

  return (
    <div className="grid gap-5">
      <p
        className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary"
        role="status"
      >
        {phaseLabel[phase]}
        {attempts.length > 0 ? ` · Tentativa ${attempts.length}` : ""}
      </p>

      <div className="panel p-5">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Frase para falar
        </p>
        <p className="mt-3 text-2xl font-medium leading-snug">{targetText}</p>
        {translation && (
          <p className="mt-2 text-sm text-text-secondary">{translation}</p>
        )}
        <div className="mt-4">
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-text-primary">
            <Volume2 className="size-4" aria-hidden />
            Ouvir frase
          </p>
          <AudioPlayer text={targetText} languageCode={languageCode} />
        </div>
      </div>

      {chunkMode && result?.practice_chunk && (
        <div className="panel border-primary/25 p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-primary">
            Trecho para praticar
          </p>
          <p className="mt-3 text-xl font-medium">{result.practice_chunk}</p>
          <p className="mt-2 text-sm text-text-secondary">{result.repair.label_pt}</p>
          <div className="mt-4">
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <Volume2 className="size-4" aria-hidden />
              Ouvir trecho
            </p>
            <AudioPlayer text={practiceText} languageCode={languageCode} />
          </div>
          <p className="mt-4 flex items-center gap-2 text-sm font-semibold">
            <Mic className="size-4" aria-hidden />
            Repetir trecho
          </p>
        </div>
      )}

      {(phase === "ready" ||
        phase === "chunk_practice" ||
        phase === "feedback" ||
        phase === "analyzing") && (
        <div className={phase === "analyzing" ? "pointer-events-none opacity-70" : undefined}>
          <Recorder
            languageCode={languageCode}
            onTranscript={(text, meta) => {
              setPhase("processing");
              void onTranscript(text, meta);
            }}
          />
        </div>
      )}

      {phase === "analyzing" && (
        <p className="text-sm text-text-secondary" role="status">
          Analisando o que o BeFluent entendeu…
        </p>
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger">
          {error}
        </p>
      )}

      {result && (phase === "feedback" || phase === "chunk_practice") && (
        <div className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            O BeFluent entendeu
          </p>
          <p className="mt-2 text-base leading-7">
            {result.transcript || "(nada foi transcrito)"}
          </p>

          {result.alignment_sequence?.length > 0 && (
            <div className="mt-5 grid gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
                  Comparação com a frase-alvo
                </p>
                <div className="mt-2">
                  <AlignmentDiff sequence={result.alignment_sequence} view="target" />
                </div>
                <ul className="mt-3 grid gap-1 text-xs text-text-secondary">
                  <li className="flex items-center gap-1.5">
                    <Check className="size-3.5 text-success" aria-hidden /> Identificado
                  </li>
                  <li className="flex items-center gap-1.5">
                    <X className="size-3.5 text-danger" aria-hidden /> Não identificado
                  </li>
                  <li className="flex items-center gap-1.5">
                    <span aria-hidden>+</span> Palavra a mais na transcrição
                  </li>
                </ul>
              </div>
            </div>
          )}

          <div
            className={`mt-5 rounded-lg border p-4 text-sm leading-6 ${
              result.success
                ? "border-success/30 bg-success/10"
                : result.status === "technical_issue"
                  ? "border-border bg-surface-elevated/50"
                  : "border-amber-500/30 bg-amber-500/5"
            }`}
            role="status"
          >
            <p className="font-semibold text-text-primary">{result.feedback.summary_pt}</p>
            {result.feedback.points
              .filter((point) => point.kind !== "good")
              .map((point) => (
                <p key={`${point.kind}-${point.token}`} className="mt-2 text-text-secondary">
                  {point.label_pt}
                </p>
              ))}
            <p className="mt-3 text-xs text-text-secondary">
              {result.feedback.metric_label_pt}
              {result.feedback.coverage != null
                ? ` · evidência de correspondência (não é nota de pronúncia)`
                : ""}
              . {result.repair.label_pt}
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            {!result.success && (
              <>
                <Button variant="secondary" onClick={resetForRetry}>
                  <Volume2 className="mr-2 size-4" aria-hidden />
                  Ouvir novamente e tentar
                </Button>
                {result.practice_chunk && !chunkMode && (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setChunkMode(true);
                      setPhase("chunk_practice");
                    }}
                  >
                    Praticar trecho
                  </Button>
                )}
              </>
            )}
            {(result.success || result.repair.allow_continue) && (
              <Button
                onClick={() => {
                  onContinue?.();
                  resetForRetry();
                }}
              >
                Continuar
              </Button>
            )}
          </div>
        </div>
      )}

      {showTransfer && transferPrompt && result?.success && (
        <div className="panel border-primary/20 p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-primary">
            Agora use com as suas palavras
          </p>
          <p className="mt-3 text-base leading-7 text-text-primary">{transferPrompt}</p>
          <p className="mt-2 text-sm text-text-secondary">
            Esta etapa é produção — não precisa repetir a frase-modelo palavra por palavra.
          </p>
          <div className="mt-4">
            <Recorder languageCode={languageCode} onTranscript={() => undefined} />
          </div>
        </div>
      )}

      {attempts.length > 1 && (
        <details className="text-sm text-text-secondary">
          <summary className="cursor-pointer font-semibold text-text-primary">
            Tentativas nesta frase ({attempts.length})
          </summary>
          <ol className="mt-2 grid gap-1">
            {attempts.map((item) => (
              <li key={item.number}>
                Tentativa {item.number}: {item.success ? "compreensível" : "a praticar"} —{" "}
                {item.summary}
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
