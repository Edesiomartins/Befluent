"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LanguageAccessState } from "@/components/language-access";

type Profile = {
  language_code: string;
  is_active: boolean;
  access_state?: LanguageAccessState;
};

/**
 * Idioma estudado ativo. Sem perfil, o código fica vazio: não abrimos uma
 * lição de inglês no lugar do idioma que o aluno escolheu.
 */
export function useActiveLanguage(): {
  code: string;
  resolved: boolean;
  accessState: LanguageAccessState;
} {
  const [code, setCode] = useState("");
  const [accessState, setAccessState] = useState<LanguageAccessState>("available");
  const [resolved, setResolved] = useState(false);

  useEffect(() => {
    let active = true;
    api<{ profiles: Profile[] }>("/api/v1/language-profiles")
      .then((response) => {
        if (!active) return;
        const profile = response.profiles.find((item) => item.is_active) ?? response.profiles[0];
        if (profile) {
          setCode(profile.language_code);
          setAccessState(profile.access_state ?? "available");
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setResolved(true);
      });
    return () => {
      active = false;
    };
  }, []);

  return { code, resolved, accessState };
}
