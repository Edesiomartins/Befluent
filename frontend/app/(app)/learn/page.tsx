"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Clock, Route, Sparkles } from "lucide-react";
import { MODES, modeColorClasses } from "@/lib/modes";
import { api } from "@/lib/api";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useTodayInCurriculum } from "@/hooks/use-curriculum";
import type { LessonModesResponse } from "@/types/lesson";

export default function LearnPage() {
  const { code, resolved } = useActiveLanguage();
  const [plan, setPlan] = useState<LessonModesResponse | null>(null);
  const today = useTodayInCurriculum(resolved ? code : null);

  useEffect(() => {
    if (!resolved) return;
    let active = true;
    api<LessonModesResponse>(`/api/v1/lessons/modes?language_code=${encodeURIComponent(code)}`)
      .then((response) => {
        if (active) setPlan(response);
      })
      .catch(() => {
        // Sem recomendação a lista continua utilizável, apenas sem priorização.
      });
    return () => {
      active = false;
    };
  }, [code, resolved]);

  const recommended = plan?.recommended_modes ?? [];
  const suggestion = MODES.find((mode) => mode.slug === recommended[0]) ?? MODES[0];
  const ordered = [
    ...MODES.filter((mode) => recommended.includes(mode.slug) && mode.slug !== suggestion.slug),
    ...MODES.filter((mode) => !recommended.includes(mode.slug) && mode.slug !== suggestion.slug),
  ];

  const weakest = plan?.weakest_skills ?? [];
  const SuggestionIcon = suggestion.icon;
  const pathDay = today.status === "ready" ? today.data.day : null;
  const pathBlock = pathDay?.blocks.find((block) => block.is_current) ?? null;

  return (
    <div>
      <p className="text-sm font-semibold text-primary">Prática</p>
      <h1 className="mt-2 page-title">O que vamos praticar?</h1>
      <p className="mt-3 max-w-2xl leading-7 text-text-secondary">
        {pathDay
          ? "O caminho do dia é a sequência principal. Abaixo, prática livre para reforçar uma competência."
          : plan?.level_is_estimated
            ? "As atividades abaixo estão calibradas pelo seu resultado no teste de nivelamento."
            : "Escolha uma habilidade para trabalhar agora. Faça o teste de nível para receber recomendações personalizadas."}
      </p>

      <Link
        href="/learn/objetivo"
        className="mt-6 flex flex-col gap-2 rounded-2xl border border-border bg-surface p-5 transition hover:border-primary/40 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <p className="text-sm font-semibold text-primary">Teaching Engine V2</p>
          <p className="mt-1 font-semibold text-text-primary">
            Objetivo EN-A1-CAN-001 — apresentar-se
          </p>
          <p className="mt-1 text-sm text-text-secondary">
            Fluxo com evidência, remediação, retry, transfer e mastery (sem “só concluir”).
          </p>
        </div>
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-primary">
          Abrir objetivo
          <ArrowRight className="size-4" aria-hidden />
        </span>
      </Link>

      {pathDay && (
        <Link
          href={`/cronograma/dia/${pathDay.id}`}
          className="mt-6 flex flex-col gap-3 rounded-2xl border border-primary/25 bg-primary-soft/50 p-5 transition hover:border-primary sm:flex-row sm:items-center sm:justify-between"
        >
          <div>
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.12em] text-primary">
              <Route className="size-3.5" aria-hidden />
              Caminho de hoje · Dia {pathDay.day_number}
            </p>
            <p className="mt-2 text-lg font-semibold">
              {pathBlock
                ? `${pathBlock.phase_label ?? "Próximo"} · ${pathBlock.skill_label}`
                : "Continuar o cronograma"}
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              {pathDay.sequence_label ??
                "Ativar → Estruturar → Compreender → Produzir → Consolidar"}
            </p>
          </div>
          <span className="inline-flex items-center gap-2 font-semibold text-primary">
            Continuar sequência <ArrowRight className="size-4" aria-hidden />
          </span>
        </Link>
      )}

      {plan && (
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-primary-soft px-2.5 py-1.5 text-xs font-semibold text-primary">
            Nível {plan.level}
          </span>
          {weakest.length > 0 && (
            <span className="rounded-md bg-surface-elevated px-2.5 py-1.5 text-xs font-medium text-text-secondary">
              Prioridade: {weakest.map((item) => item.label).join(", ")}
            </span>
          )}
          {!plan.level_is_estimated && (
            <Link href="/placement-test" className="text-xs font-semibold text-primary hover:underline">
              Fazer teste de nível
            </Link>
          )}
        </div>
      )}

      <Link
        href={`/learn/${suggestion.slug}`}
        className="mt-8 grid gap-5 rounded-2xl bg-[var(--primary-deep)] p-6 text-white transition hover:brightness-110 sm:grid-cols-[1fr_auto] sm:items-center"
      >
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[.14em] text-white/60">
            {recommended.length > 0 && <Sparkles className="size-3.5" aria-hidden />}
            {recommended.length > 0 ? "Recomendado para você" : "Sugestão inicial"}
          </p>
          <h2 className="mt-2 flex items-center gap-2 text-xl font-semibold">
            <SuggestionIcon className="size-5" aria-hidden />
            {suggestion.title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-white/70">
            {weakest.length > 0
              ? `Prioriza ${weakest[0].label.toLowerCase()}, sua competência mais fraca no teste.`
              : suggestion.description}
          </p>
        </div>
        <span className="inline-flex items-center gap-2 font-semibold">
          Começar <ArrowRight className="size-4" aria-hidden />
        </span>
      </Link>

      <div className="mt-9 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ordered.map((mode) => {
          const Icon = mode.icon;
          const colors = modeColorClasses[mode.color];
          const isRecommended = recommended.includes(mode.slug);
          return (
            <Link
              href={`/learn/${mode.slug}`}
              key={mode.slug}
              className={`panel group flex items-start gap-3 p-4 transition hover:-translate-y-0.5 ${colors.ring} ${
                isRecommended ? "border-primary" : ""
              }`}
            >
              <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${colors.bg} ${colors.text}`}>
                <Icon className="size-5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="font-semibold group-hover:text-primary">
                  {mode.title}
                  {isRecommended && (
                    <span className="ml-2 rounded-full bg-primary-soft px-2 py-0.5 text-[.65rem] font-bold uppercase tracking-wide text-primary">
                      Recomendado
                    </span>
                  )}
                </h2>
                <p className="mt-1 text-sm leading-6 text-text-secondary">{mode.description}</p>
                <p className="mt-2 flex items-center gap-1 text-xs font-medium text-text-secondary">
                  <Clock className="size-3.5" aria-hidden />
                  {mode.duration}
                </p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
