"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { NativeLanguageForm } from "@/components/native-language-form";
import { NativeLanguageProvider } from "@/components/native-language-context";
import {
  cachedNativeLanguage,
  loadNativeLanguage,
  nativeLanguageBlocksPath,
  type NativeLanguageState,
} from "@/lib/native-language";

export function NativeLanguageGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [state, setState] = useState<NativeLanguageState | null>(cachedNativeLanguage);
  const blocks = nativeLanguageBlocksPath(pathname);

  useEffect(() => {
    let active = true;
    loadNativeLanguage()
      .then((next) => {
        if (active) setState(next);
      })
      .catch(() => {
        if (active) setState({ contractActive: false, code: null, options: [] });
      });
    return () => {
      active = false;
    };
  }, [pathname]);

  if (!state) {
    return (
      <p className="text-sm text-text-secondary" role="status">
        Verificando sua língua nativa…
      </p>
    );
  }

  const needsChoice = state.contractActive && !state.code && blocks;
  if (needsChoice) {
    return (
      <NativeLanguageForm
        onSaved={(code) => setState({ contractActive: true, code, options: state?.options ?? [] })}
      />
    );
  }

  return <NativeLanguageProvider code={state.code}>{children}</NativeLanguageProvider>;
}
