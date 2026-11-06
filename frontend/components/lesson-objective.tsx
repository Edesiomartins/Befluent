"use client";

import { AudioPlayer } from "@/components/study";
import { speechText } from "@/lib/bilingual";

/**
 * O objetivo pode trazer a instrução na língua nativa e um trecho no idioma
 * estudado. O áudio recebe só esse trecho.
 */
export function LessonObjective({
  objective,
  objectiveTarget,
  targetLanguage,
  nativeLanguage,
}: {
  objective?: string | null;
  objectiveTarget?: string | null;
  targetLanguage?: string | null;
  nativeLanguage?: string | null;
}) {
  const support = objective?.trim() ?? "";
  const target = objectiveTarget?.trim() ?? "";
  const spoken = speechText(target);
  if (!support && !spoken) return null;

  return (
    <div className="mt-3 max-w-2xl">
      <p className="font-semibold text-text-primary">Objetivo</p>
      {spoken && (
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <p lang={targetLanguage || undefined} className="text-xl font-medium leading-8 text-text-primary">
            {target}
          </p>
          <AudioPlayer
            variant="compact"
            label="Ouvir"
            accessibleName="Ouvir o objetivo no idioma estudado"
            text={spoken}
            languageCode={targetLanguage || undefined}
          />
        </div>
      )}
      {support && (
        <p lang={nativeLanguage || undefined} className="mt-2 leading-7 text-text-secondary">
          {support}
        </p>
      )}
    </div>
  );
}
