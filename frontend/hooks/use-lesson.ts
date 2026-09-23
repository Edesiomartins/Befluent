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
 * `languageCode` nulo: ainda não há idioma resolvido — não dispara generate
 * com um fallback temporário. Só a resposta do pedido mais recente atualiza
 * o estado (troca de idioma ou remount não deixa resposta antiga sobrescrever).
 */
export function useLesson<T extends LessonEnvelope>(
  mode: string,
  languageCode: string | null = null,
) {
  const [state, setState] = useState<State<T>>({
    status: "loading",
    lesson: null,
    error: null,
    rawError: null,
  });
  const requested = useRef<string | null>(null);
  const requestSeq = useRef(0);

  const load = useCallback(async () => {
    if (!languageCode) return;
    const seq = ++requestSeq.current;
    setState({ status: "loading", lesson: null, error: null, rawError: null });
    try {
      const lesson = await api<T>("/api/v1/lessons/generate", {
        method: "POST",
        body: { language_code: languageCode, mode },
      });
      if (seq !== requestSeq.current) return;
      setState({ status: "ready", lesson, error: null, rawError: null });
    } catch (caught) {
      if (seq !== requestSeq.current) return;
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
    if (!languageCode) {
      requested.current = null;
      requestSeq.current += 1;
      setState({ status: "loading", lesson: null, error: null, rawError: null });
      return;
    }
    const key = `${mode}:${languageCode}`;
    if (requested.current === key) return;
    requested.current = key;
    void load();
  }, [mode, languageCode, load]);

  useEffect(() => {
    return () => {
      requestSeq.current += 1;
    };
  }, []);

  return { ...state, reload: load };
}
