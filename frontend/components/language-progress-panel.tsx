"use client";

import { usePrefersReducedMotion } from "@/hooks/use-prefers-reduced-motion";

export type ProgressSkill = {
  skill: string;
  label: string;
  percent: number;
};

export type LanguageProgress = {
  auto_promotion_enabled?: boolean;
  cefr?: {
    current: string | null;
    next: string | null;
    progress_to_next_percent: number | null;
  } | null;
  milestone?: { code: string; index: number; level: string } | null;
  skills?: ProgressSkill[];
  next_milestone?: { code: string; hint: string | null } | null;
  latest_achievement?: { title: string | null } | null;
};

export function LanguageProgressPanel({ progress }: { progress: LanguageProgress }) {
  const current = progress.cefr?.current;
  const next = progress.cefr?.next;
  const skills = progress.skills ?? [];
  const towardNext = progress.cefr?.progress_to_next_percent;

  return (
    <section className="panel mt-8 p-6 sm:p-8" aria-label="Progresso no idioma">
      <h2 className="font-display text-2xl font-medium tracking-tight">Seu nível atual</h2>
      {current ? (
        <p className="mt-3 font-display text-5xl leading-none">{current}</p>
      ) : (
        <p className="mt-3 text-sm text-text-secondary">
          O nível deste idioma ainda não foi definido.
        </p>
      )}
      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        {next && (
          <div>
            <dt className="text-xs text-text-secondary">Próximo nível da escala</dt>
            <dd className="mt-1 text-lg font-semibold">{next}</dd>
          </div>
        )}
        {progress.milestone && (
          <div>
            <dt className="text-xs text-text-secondary">Marco atual</dt>
            <dd className="mt-1 text-lg font-semibold">{progress.milestone.code}</dd>
          </div>
        )}
      </dl>
      {towardNext != null && (
        <p className="mt-4 text-sm">Progresso para {next}: {towardNext}%</p>
      )}
      {skills.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold">Habilidades</h3>
          <ul className="mt-3 space-y-3">
            {skills.map((skill) => (
              <li key={skill.skill}>
                <div className="flex justify-between gap-4 text-sm">
                  <span>{skill.label}</span>
                  <span className="tabular-nums text-text-secondary">{skill.percent}%</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-soft">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${skill.percent}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {progress.next_milestone?.hint && (
        <div className="mt-6 border-t border-border pt-5">
          <h3 className="text-sm font-semibold">Próximo marco</h3>
          <p className="mt-2 text-sm leading-6 text-text-secondary">{progress.next_milestone.hint}</p>
        </div>
      )}
      {progress.latest_achievement?.title && (
        <div className="mt-6 border-t border-border pt-5">
          <h3 className="text-sm font-semibold">Última conquista</h3>
          <p className="mt-2 text-sm">{progress.latest_achievement.title}</p>
        </div>
      )}
    </section>
  );
}

export function AchievementCelebration({
  title,
  detail,
  kind,
  onClose,
}: {
  title: string;
  detail?: string | null;
  kind: "milestone" | "cefr";
  onClose: () => void;
}) {
  const reduced = usePrefersReducedMotion();
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="achievement-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className={`panel relative max-w-md p-8 text-center ${reduced ? "" : "achievement-pop"}`}>
        {!reduced && kind === "cefr" && (
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 flex justify-center gap-3" data-testid="confetti">
            <span className="confetti-bit bg-primary" />
            <span className="confetti-bit bg-amber-400" />
            <span className="confetti-bit bg-emerald-500" />
          </div>
        )}
        <p className="text-sm text-text-secondary">{kind === "cefr" ? "Parabéns!" : "Você avançou!"}</p>
        <h2 id="achievement-title" className="mt-2 font-display text-4xl">{title}</h2>
        {detail && <p className="mt-3 text-sm leading-6 text-text-secondary">{detail}</p>}
        <button
          type="button"
          className="mt-6 min-h-11 rounded-xl bg-primary px-5 text-sm font-semibold text-white"
          onClick={onClose}
        >
          Fechar
        </button>
      </div>
    </div>
  );
}
