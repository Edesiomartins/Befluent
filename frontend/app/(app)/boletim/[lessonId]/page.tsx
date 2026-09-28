"use client";

/**
 * Boletim da lição: a correção que sobrevive ao fim da sessão.
 *
 * O feedback já existia na tela, no instante da resposta, e se perdia. Esta
 * página lê os snapshots gravados em `learning_attempts.report_json` — o que o
 * aluno viu naquele momento, não uma correção remontada depois.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { EmptyState, ErrorState, Loading, Note } from "@/components/ui";

type ReportEntry = {
  id: string;
  activity_type: string;
  prompt: string;
  student_response: string;
  correct_answer: string;
  result: string;
  why_selected: string;
  why_correct: string;
  remember: string;
  term: string;
  attempt_number: number;
  answered_at: string | null;
};

type LessonReport = {
  lesson: { id: string; title: string; objective: string | null; status: string };
  entries: ReportEntry[];
  summary: { total: number; incorrect: number; correct: number };
  disclaimer: string;
};

const ACTIVITY_LABELS: Record<string, string> = {
  multiple_choice: "Gramática",
  recognition: "Reconhecimento",
  reverse_recognition: "Reconhecimento inverso",
  listening_recognition: "Escuta",
  lexical_production: "Produção",
  guided_production: "Produção guiada",
  free_production: "Produção livre",
  fill_gap: "Lacuna",
  word_order: "Ordem das palavras",
  transfer_question: "Transferência",
};

function activityLabel(type: string) {
  return ACTIVITY_LABELS[type] ?? type;
}

export default function LessonReportPage() {
  const params = useParams<{ lessonId: string }>();
  const lessonId = params?.lessonId;
  const [report, setReport] = useState<LessonReport | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!lessonId) return;
    let active = true;
    api(`/api/v1/lessons/${lessonId}/report`)
      .then((payload) => {
        if (active) setReport(payload as LessonReport);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError ? caught.message : "Não foi possível abrir o boletim.",
        );
      });
    return () => {
      active = false;
    };
  }, [lessonId]);

  if (error) return <ErrorState message={error} />;
  if (!report) return <Loading label="Abrindo o boletim" />;

  const { entries, summary } = report;

  return (
    <div className="mx-auto max-w-3xl">
      <p className="label">Boletim da lição</p>
      <h1 className="page-title mt-1">{report.lesson.title}</h1>
      {report.lesson.objective && (
        <p className="mt-2 text-sm leading-6 text-text-secondary">{report.lesson.objective}</p>
      )}

      {summary.total > 0 && (
        <p className="mt-5 text-sm text-text-secondary">
          {summary.total} {summary.total === 1 ? "resposta" : "respostas"} com correção
          registrada · {summary.incorrect} para revisar.
        </p>
      )}

      <Note className="mt-4">{report.disclaimer}</Note>

      {entries.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="Nenhuma resposta registrada"
            description="Esta lição ainda não tem resposta com correção guardada. Ao responder, cada correção aparece aqui."
          />
        </div>
      ) : (
        <ol className="mt-6 grid gap-4">
          {entries.map((entry, index) => {
            const wrong = entry.result === "incorrect";
            return (
              <li key={entry.id} className="panel p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="label">
                    {index + 1}. {activityLabel(entry.activity_type)}
                    {entry.term ? ` · ${entry.term}` : ""}
                  </p>
                  <p className={`text-sm ${wrong ? "text-danger" : "text-text-secondary"}`}>
                    {wrong ? "Para revisar" : "Correta"}
                  </p>
                </div>

                {entry.prompt && <p className="mt-3 leading-7">{entry.prompt}</p>}

                <dl className="mt-4 grid gap-2 text-sm">
                  <div className="flex flex-wrap gap-2">
                    <dt className="text-text-secondary">Sua resposta:</dt>
                    <dd className={wrong ? "font-medium text-danger" : "font-medium"}>
                      {entry.student_response || "—"}
                    </dd>
                  </div>
                  {wrong && entry.correct_answer && (
                    <div className="flex flex-wrap gap-2">
                      <dt className="text-text-secondary">Resposta certa:</dt>
                      <dd className="font-medium">{entry.correct_answer}</dd>
                    </div>
                  )}
                </dl>

                {(entry.why_selected || entry.why_correct || entry.remember) && (
                  <div className="mt-4 grid gap-2 border-t border-border pt-4 text-sm leading-6 text-text-secondary">
                    {entry.why_selected && <p>{entry.why_selected}</p>}
                    {entry.why_correct && <p>{entry.why_correct}</p>}
                    {entry.remember && <p>{entry.remember}</p>}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}

      <p className="mt-8 text-sm">
        <Link href="/learn" className="text-primary hover:underline">
          Voltar para o estudo
        </Link>
      </p>
    </div>
  );
}
