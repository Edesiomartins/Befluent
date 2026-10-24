"use client";

import { useEffect } from "react";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { accentFor } from "@/lib/language-accent";

export function LanguageAccent() {
  const { code, resolved } = useActiveLanguage();

  useEffect(() => {
    const root = document.documentElement;
    const accent = accentFor(resolved ? code : null);
    root.dataset.targetLanguage = resolved && code ? code : "";
    root.style.setProperty("--language-accent", accent.ink);
    root.style.setProperty("--language-accent-soft", accent.soft);
  }, [code, resolved]);

  return null;
}
