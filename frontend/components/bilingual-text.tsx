import type { ReactNode } from "react";
import { resolveSupportVisibility, type SupportVisibility } from "@/lib/bilingual";

const nativeClass: Record<Exclude<SupportVisibility, "off">, string> = {
  prominent: "mt-1 text-base leading-7 text-text-secondary",
  discreet: "mt-1 text-sm leading-6 text-text-secondary",
  spot: "mt-1 text-xs leading-5 text-text-secondary",
  expandable: "mt-2 text-sm leading-6 text-text-secondary",
};

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
}: {
  target: string;
  native?: string | null;
  visibility?: string | null;
  heading?: boolean;
  audio?: ReactNode;
}) {
  const mode = resolveSupportVisibility(visibility);
  const support = native?.trim() && native.trim() !== target.trim() ? native.trim() : "";
  const showSupport = Boolean(support) && mode !== "off";
  const TargetTag = heading ? "h2" : "p";

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <TargetTag
          className={
            heading
              ? "text-2xl font-semibold tracking-tight text-text-primary"
              : "font-medium text-text-primary"
          }
        >
          {target}
        </TargetTag>
        {audio}
      </div>
      {showSupport && mode === "expandable" && (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm font-semibold text-primary">Ver apoio</summary>
          <p className={nativeClass.expandable}>{support}</p>
        </details>
      )}
      {showSupport && mode !== "expandable" && <p className={nativeClass[mode]}>{support}</p>}
    </div>
  );
}
