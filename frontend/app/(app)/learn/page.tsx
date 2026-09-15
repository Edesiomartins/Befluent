"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Route, Sparkles, Target } from "lucide-react";
import { MODE_SECTION_LABEL, MODES, resolveRecommendedSlug, type ModeSection } from "@/lib/modes";
import { ModeCard } from "@/components/mode-card";
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

  // O backend recomenda por slug técnico e nunca recomenda "voice" (ver
  // lib/modes.ts); o alias só casa essa recomendação com o card certo do
  // hub, sem alterar a lista que vem do backend.
  const recommended = (plan?.recommended_modes ?? []).map(resolveRecommendedSlug);
  const suggestion = MODES.find((mode) => mode.slug === recommended[0]) ?? MODES[0];

  const SECTIONS: ModeSection[] = ["recommended", "skill", "assessment"];

  const weakest = plan?.weakest_skills ?? [];
  const SuggestionIcon = suggestion.icon;
  const pathDay = today.status === "ready" ? today.data.day : null;
  const pathBlock = pathDay?.blocks.find((block) => block.is_current) ?? null;

  return (
    <div>
      <h1 className="page-title">O que vamos praticar?</h1>
      <p className="mt-3 max-w-2xl leading-7 text-text-secondary">
        {pathDay
          ? "Reforce uma habilidade fora da sequência do dia."
          : plan?.level_is_estimated
            ? "As atividades abaixo estão calibradas pelo seu resultado no teste de nivelamento."
            : "Escolha uma habilidade para trabalhar agora. Faça o teste de nível para receber recomendações personalizadas."}
      </p>

      {pathDay && (
        <Link
          href={`/cronograma/dia/${pathDay.id}`}
          className="mt-6 flex flex-col gap-3 rounded-xl border border-border bg-surface px-5 py-4 transition-colors hover:border-primary/50 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-center gap-3">
            <Route className="size-4 shrink-0 text-primary" aria-hidden />
            <p className="text-sm">
              <span className="text-text-secondary">Caminho de hoje, dia {pathDay.day_number}: </span>
              <span className="font-semibold">
                {pathBlock
                  ? `${pathBlock.phase_label ?? "Próximo"} · ${pathBlock.skill_label}`
                  : "Continuar o cronograma"}
              </span>
            </p>
          </div>
          <span className="inline-flex items-center gap-2 text-sm font-semibold text-primary">
            Continuar sequência <ArrowRight className="size-4" aria-hidden />
          </span>
        </Link>
      )}

      <Link
        href="/learn/objetivo"
        className={`${pathDay ? "mt-2" : "mt-6"} flex flex-col gap-3 rounded-xl border border-border bg-surface px-5 py-4 transition-colors hover:border-primary/50 sm:flex-row sm:items-center sm:justify-between`}
      >
        <div className="flex items-center gap-3">
          <Target className="size-4 shrink-0 text-primary" aria-hidden />
          <p className="text-sm">
            <span className="text-text-secondary">Objetivo guiado: </span>
            <span className="font-semibold">apresentar-se</span>
            <span className="text-text-secondary"> — pratique até demonstrar, com nova tentativa</span>
          </p>
        </div>
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-primary">
          Abrir objetivo
          <ArrowRight className="size-4" aria-hidden />
        </span>
      </Link>

      {plan && (
        <div className="mt-8 flex flex-wrap items-baseline gap-x-5 gap-y-1 text-sm text-text-secondary">
          <span>
            Nível <span className="font-semibold text-text-primary">{plan.level}</span>
          </span>
          {weakest.length > 0 && (
            <span>
              Prioridade:{" "}
              <span className="font-semibold text-text-primary">
                {weakest.map((item) => item.label).join(", ")}
              </span>
            </span>
          )}
          {!plan.level_is_estimated && (
            <Link href="/placement-test" className="font-semibold text-primary hover:underline">
              Fazer teste de nível
            </Link>
          )}
        </div>
      )}

      <Link
        href={`/learn/${suggestion.slug}`}
        className={`${plan ? "mt-3" : "mt-8"} grid gap-5 rounded-2xl bg-[var(--primary-deep)] p-6 text-white transition hover:brightness-110 sm:grid-cols-[1fr_auto] sm:items-center sm:p-7`}
      >
        <div>
          <p className="flex items-center gap-2 text-sm text-white/65">
            {recommended.length > 0 && <Sparkles className="size-3.5" aria-hidden />}
            {recommended.length > 0 ? "Recomendado para você" : "Sugestão inicial"}
          </p>
          <h2 className="mt-2 flex items-center gap-3 font-display text-[1.75rem] font-medium leading-tight">
            <SuggestionIcon className="size-5 shrink-0 text-white/70" aria-hidden />
            {suggestion.title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-white/70">
            {weakest.length > 0
              ? `Prioriza ${weakest[0].label.toLowerCase()}, sua competência mais fraca no teste.`
              : suggestion.description}
          </p>
        </div>
        <span className="inline-flex min-h-11 items-center gap-2 justify-self-start rounded-xl bg-white px-5 text-sm font-semibold text-[var(--primary-deep)]">
          Começar <ArrowRight className="size-4" aria-hidden />
        </span>
      </Link>

      {SECTIONS.map((section) => {
        const modes = MODES.filter((mode) => mode.section === section);
        if (modes.length === 0) return null;
        return (
          <section key={section} className="mt-9">
            <h2 className="section-title">{MODE_SECTION_LABEL[section]}</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {modes.map((mode) => (
                <ModeCard
                  key={mode.slug}
                  mode={mode}
                  // Só o grupo "Pratique uma habilidade" mostra o selo dinâmico
                  // de recomendação — nos outros dois grupos ele duplicaria o
                  // que o próprio título da seção já diz (Recomendado/Avaliação).
                  recommended={section === "skill" && recommended.includes(mode.slug)}
                  titleAs="h3"
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
