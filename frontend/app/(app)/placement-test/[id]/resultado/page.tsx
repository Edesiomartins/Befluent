"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, ErrorState, Loading } from "@/components/ui";
import { SKILL_LABELS, levelShortCode } from "@/lib/levels";
import { createCurriculum } from "@/hooks/use-curriculum";
import { DURATIONS, type Duration } from "@/types/curriculum";
import type { PlacementResult, SkillResult } from "@/types/placement";

const STATUS_LABELS: Record<SkillResult["status"], string> = {
  assessed: "",
  not_assessed: "não avaliada",
  not_available: "não avaliada",
};

const accuracy = (skill: SkillResult) => skill.score / Math.max(skill.max_score, 1);

/** Competências ordenadas da mais forte para a mais fraca, ou null se empatadas.
 *
 *  Sem diferença real de desempenho não faz sentido apontar "ponto forte" e
 *  "ponto fraco": seriam a mesma competência, gerando texto contraditório.
 */
function rankSkills(result: PlacementResult): SkillResult[] | null {
  const assessed = result.skills.filter((skill) => skill.status === "assessed");
  if (assessed.length < 2) return null;
  const ranked = [...assessed].sort((a, b) => accuracy(b) - accuracy(a));
  const spread = accuracy(ranked[0]) - accuracy(ranked[ranked.length - 1]);
  return spread > 0.01 ? ranked : null;
}

function skillMessage(result: PlacementResult, ranked: SkillResult[] | null): string {
  if (!result.overall_level) {
    return "Responda a mais atividades para uma estimativa mais precisa.";
  }
  if (!ranked) {
    return "Seu desempenho ficou equilibrado entre as competências avaliadas.";
  }
  const weakest = ranked[ranked.length - 1];
  return `Seu ponto de maior desenvolvimento no momento é ${SKILL_LABELS[weakest.skill].toLowerCase()}.`;
}

/** Oferta do cronograma logo após o resultado.
 *
 *  É aqui que o nivelamento deixa de ser um número e vira um plano: os níveis
 *  por competência que acabaram de ser gravados definem o ponto de entrada.
 */
function BuildCurriculum({ languageCode }: { languageCode: string }) {
  const router = useRouter();
  const [duration, setDuration] = useState<Duration>(90);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setSaving(true);
    setError("");
    try {
      await createCurriculum(languageCode, duration);
      router.push("/cronograma");
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível gerar seu cronograma.",
      );
      setSaving(false);
    }
  }

  return (
    <section className="panel mt-5 p-6">
      <h2 className="section-title">Monte seu cronograma</h2>
      <p className="mt-2 text-sm leading-6 text-text-secondary">
        Transforme este resultado em um plano diário, com blocos das oito áreas de
        estudo e checkpoints a cada duas semanas.
      </p>

      <fieldset className="mt-5">
        <legend className="sr-only">Duração do cronograma</legend>
        <div className="grid gap-3 sm:grid-cols-2">
          {DURATIONS.map((value) => (
            <label
              key={value}
              className={`cursor-pointer rounded-xl border-2 p-4 transition ${
                duration === value
                  ? "border-primary bg-primary-soft"
                  : "border-border bg-surface hover:border-primary/40"
              }`}
            >
              <input
                className="sr-only"
                type="radio"
                name="curriculum_duration"
                value={value}
                checked={duration === value}
                onChange={() => setDuration(value)}
              />
              <span
                className={`block text-sm font-bold ${duration === value ? "text-primary" : ""}`}
              >
                {value} dias
              </span>
              <span className="mt-1 block text-sm text-text-secondary">
                {value === 90
                  ? "Ritmo intensivo, dois subníveis a partir da sua entrada."
                  : "Ritmo sustentável, meta B2."}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {error && (
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}
        </p>
      )}

      <Button className="mt-5" loading={saving} disabled={saving} onClick={() => void submit()}>
        Gerar cronograma
      </Button>
    </section>
  );
}

export default function PlacementResultPage() {
  const params = useParams<{ id: string }>();
  const testId = params.id;
  const [result, setResult] = useState<PlacementResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api<PlacementResult>(`/api/v1/placement-tests/${testId}/result`)
      .then((payload) => {
        if (active) setResult(payload);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar seu resultado.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [testId]);

  if (loading) return <Loading label="Calculando seu resultado" />;
  if (error || !result) return <ErrorState message={error} />;

  const notAssessed = result.skills.filter((skill) => skill.status !== "assessed");
  const ranked = rankSkills(result);
  const hasPriorities = result.recommendations.length > 0;

  return (
    <div className="mx-auto max-w-3xl">
      <p className="text-sm font-semibold text-primary">Resultado</p>
      <h1 className="mt-2 page-title">Seu nível estimado</h1>

      <section className="panel mt-7 p-6">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-2">
          <span className="text-4xl font-bold tracking-tight text-primary">
            {levelShortCode(result.overall_level) ?? "—"}
          </span>
          <span className="text-lg font-semibold">{result.overall?.name_pt}</span>
        </div>
        {result.overall && (
          <p className="mt-3 leading-7 text-text-secondary">{result.overall.short_description}</p>
        )}
        <p className="mt-4 text-sm text-text-secondary">{skillMessage(result, ranked)}</p>

        {result.confidence_score != null && (
          <p className="mt-4 text-sm">
            <span className="text-text-secondary">Confiança da estimativa: </span>
            <span className="font-semibold">
              {result.confidence_label} ({Math.round(result.confidence_score)}/100)
            </span>
          </p>
        )}
        <p className="mt-4 border-t border-border pt-4 text-sm text-text-secondary">
          {result.disclaimer}
        </p>
      </section>

      <section className="panel mt-5 p-6">
        <h2 className="section-title">Competências</h2>
        <ul className="mt-4 grid gap-3">
          {result.skills.map((skill) => (
            <li
              key={skill.skill}
              className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3 text-sm last:border-0 last:pb-0"
            >
              <span className="font-medium">{skill.label}</span>
              {skill.status === "assessed" ? (
                <span className="font-semibold text-primary">
                  {levelShortCode(skill.estimated_level)}
                </span>
              ) : (
                <span className="text-text-secondary">{STATUS_LABELS[skill.status]}</span>
              )}
            </li>
          ))}
        </ul>
        {notAssessed.length > 0 && (
          <p className="mt-4 text-sm text-text-secondary">
            Competências não avaliadas não entraram no cálculo do nível geral.
            {!result.speaking_available && " A avaliação de fala ainda não está disponível."}
          </p>
        )}
      </section>

      {(ranked || hasPriorities) && (
        <section className="panel mt-5 p-6">
          <h2 className="section-title">
            {ranked ? "Pontos fortes e prioridades" : "Prioridades de estudo"}
          </h2>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            {ranked && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
                  Ponto forte
                </p>
                <p className="mt-2 text-sm font-medium">{ranked[0].label}</p>
              </div>
            )}
            {hasPriorities && (
              <div>
                {ranked && (
                  <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
                    Prioridades de estudo
                  </p>
                )}
                <ul className="mt-2 grid gap-1.5 text-sm">
                  {result.recommendations.slice(0, 4).map((item) => (
                    <li key={`${item.skill}-${item.reason}`}>
                      {SKILL_LABELS[item.skill]}
                      <span className="text-text-secondary">
                        {item.reason === "not_assessed"
                          ? " — avaliar futuramente"
                          : " — abaixo do nível geral"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      <BuildCurriculum languageCode={result.language_code} />

      <div className="mt-7 flex flex-wrap gap-3 border-t border-border pt-6">
        <Link
          href="/dashboard"
          className="inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)]"
        >
          Ir para o dashboard
        </Link>
        <Link
          href="/learn"
          className="inline-flex min-h-11 items-center rounded-xl border-2 border-border bg-surface px-5 text-sm font-bold shadow-[0_4px_0_var(--secondary-shadow)] hover:bg-surface-elevated"
        >
          Começar a praticar
        </Link>
      </div>
    </div>
  );
}
