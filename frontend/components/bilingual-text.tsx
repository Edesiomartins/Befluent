import type { ReactNode } from "react";
import { resolveSupportVisibility, type SupportVisibility } from "@/lib/bilingual";

const nativeClass: Record<Exclude<SupportVisibility, "off">, string> = {
  prominent: "mt-3 border-t border-border pt-3 text-base leading-7 text-text-secondary",
  discreet: "mt-3 border-t border-border pt-3 text-sm leading-6 text-text-secondary",
  spot: "mt-3 border-t border-border pt-3 text-xs leading-5 text-text-secondary",
  expandable: "mt-2 text-sm leading-6 text-text-secondary",
};

export const targetUtteranceClass = "min-w-0 flex-1 text-xl font-medium leading-8 text-text-primary";

export function TargetLine({
  text,
  audio,
  lang,
}: {
  text: string;
  audio?: ReactNode;
  lang?: string | null;
}) {
  return (
    <div className="flex items-start gap-3">
      <p lang={lang || undefined} className={targetUtteranceClass}>{text}</p>
      {audio ? <div className="shrink-0">{audio}</div> : null}
    </div>
  );
}

/**
 * Língua estudada em destaque e apoio nativo por baixo.
 * Não acrescenta uma terceira linha.
 */
export function BilingualText({
  target,
  native,
  visibility,
  heading = false,
  audio,
  targetLang,
  nativeLang,
}: {
  target: string;
  native?: string | null;
  visibility?: string | null;
  heading?: boolean;
  audio?: ReactNode;
  targetLang?: string | null;
  nativeLang?: string | null;
}) {
  const mode = resolveSupportVisibility(visibility);
  const support = native?.trim() && native.trim() !== target.trim() ? native.trim() : "";
  const showSupport = Boolean(support) && mode !== "off";
  const TargetTag = heading ? "h2" : "p";

  return (
    <div>
      <div className="flex items-start gap-3">
        <TargetTag
          lang={targetLang || undefined}
          className={heading ? `${targetUtteranceClass} text-xl` : targetUtteranceClass}
        >
          {target}
        </TargetTag>
        {audio ? <div className="shrink-0">{audio}</div> : null}
      </div>
      {showSupport && mode === "expandable" && (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm font-semibold text-primary">Ver apoio</summary>
          <p lang={nativeLang || undefined} className={nativeClass.expandable}>{support}</p>
        </details>
      )}
      {showSupport && mode !== "expandable" && (
        <p lang={nativeLang || undefined} className={nativeClass[mode]}>{support}</p>
      )}
    </div>
  );
}
