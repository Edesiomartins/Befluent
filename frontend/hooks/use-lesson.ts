"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { LessonEnvelope } from "@/types/lesson";

type State<T> =
  | { status: "loading"; lesson: null; error: null; rawError: null }
  | { status: "ready"; lesson: T; error: null; rawError: null }
  | { status: "error"; lesson: null; error: string; rawError: unknown };

/**
 * Gera (e persiste) uma lição adaptada ao nível do aluno para o modo pedido.
 *
 * A geração acontece uma vez por montagem — regenerar a cada render criaria
 * uma lição nova no histórico a cada re-render.
 */
export function useLesson<T extends LessonEnvelope>(mode: string, languageCode = "en") {
  const [state, setState] = useState<State<T>>({
    status: "loading",
    lesson: null,
    error: null,
    rawError: null,
  });
  const requested = useRef<string | null>(null);

  const load = useCallback(async () => {
    setState({ status: "loading", lesson: null, error: null, rawError: null });
    try {
      const lesson = await api<T>("/api/v1/lessons/generate", {
        method: "POST",
        body: { language_code: languageCode, mode },
      });
      setState({ status: "ready", lesson, error: null, rawError: null });
    } catch (caught) {
      setState({
        status: "error",
        lesson: null,
        error:
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível gerar a lição. Tente novamente.",
        rawError: caught,
      });
    }
  }, [mode, languageCode]);

  useEffect(() => {
    const key = `${mode}:${languageCode}`;
    if (requested.current === key) return;
    requested.current = key;
    void load();
  }, [mode, languageCode, load]);

  return { ...state, reload: load };
}
