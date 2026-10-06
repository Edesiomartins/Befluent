"use client";

import { createContext, useContext, type ReactNode } from "react";

const NativeLanguageContext = createContext<string | null>(null);

export function NativeLanguageProvider({
  code,
  children,
}: {
  code: string | null;
  children: ReactNode;
}) {
  return <NativeLanguageContext.Provider value={code}>{children}</NativeLanguageContext.Provider>;
}

/** Código da língua nativa, ou null quando o contrato ainda não a declarou. */
export function useLearnerNativeLanguage(): string | null {
  return useContext(NativeLanguageContext);
}
