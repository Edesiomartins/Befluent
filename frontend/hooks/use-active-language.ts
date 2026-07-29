"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Profile = { language_code: string; is_active: boolean };

/**
 * Idioma ativo do usuário, com fallback silencioso para inglês.
 * Falha de rede não deve impedir a página de estudo de abrir.
 */
export function useActiveLanguage(): { code: string; resolved: boolean } {
  const [code, setCode] = useState("en");
  const [resolved, setResolved] = useState(false);

  useEffect(() => {
    let active = true;
    api<{ profiles: Profile[] }>("/api/v1/language-profiles")
      .then((response) => {
        if (!active) return;
        const profile =
          response.profiles.find((item) => item.is_active) ?? response.profiles[0];
        if (profile) setCode(profile.language_code);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setResolved(true);
      });
    return () => {
      active = false;
    };
  }, []);

  return { code, resolved };
}
