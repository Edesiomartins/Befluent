"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type {
  ActiveCurriculum,
  Curriculum,
  DayDetail,
  Duration,
  RescheduleStrategy,
  TodayPayload,
} from "@/types/curriculum";

type State<T> =
  | { status: "loading"; data: null; error: null; code: null }
  | { status: "ready"; data: T; error: null; code: null }
  | { status: "error"; data: null; error: string; code: string | null };

const LOADING = { status: "loading", data: null, error: null, code: null } as const;

function failure<T>(caught: unknown, fallback: string): State<T> {
  return {
    status: "error",
    data: null,
    error: caught instanceof ApiError ? caught.message : fallback,
    code: caught instanceof ApiError ? (caught.code ?? null) : null,
  };
}

/**
 * Busca um recurso do cronograma.
 *
 * O `code` do erro é preservado: a página precisa distinguir "ainda não existe
 * cronograma" (convite a criar) de "falhou ao carregar" (tentar de novo). Sem
 * isso, quem nunca gerou um cronograma veria uma mensagem de erro.
 */
function useCurriculumResource<T>(path: string | null, fallbackMessage: string) {
  const [state, setState] = useState<State<T>>(LOADING);

  const load = useCallback(async () => {
    if (!path) return;
    setState(LOADING);
    try {
      setState({ status: "ready", data: await api<T>(path), error: null, code: null });
    } catch (caught) {
      setState(failure<T>(caught, fallbackMessage));
    }
  }, [path, fallbackMessage]);

  useEffect(() => {
    let active = true;
    if (!path) return;
    setState(LOADING);
    api<T>(path)
      .then((data) => {
        if (active) setState({ status: "ready", data, error: null, code: null });
      })
      .catch((caught) => {
        if (active) setState(failure<T>(caught, fallbackMessage));
      });
    return () => {
      active = false;
    };
  }, [path, fallbackMessage]);

  return { ...state, reload: load };
}

export function useActiveCurriculum(languageCode: string | null) {
  return useCurriculumResource<ActiveCurriculum>(
    languageCode ? `/api/v1/curriculum/active?language_code=${encodeURIComponent(languageCode)}` : null,
    "Não foi possível carregar seu cronograma.",
  );
}

export function useTodayInCurriculum(languageCode: string | null) {
  return useCurriculumResource<TodayPayload>(
    languageCode ? `/api/v1/curriculum/day/today?language_code=${encodeURIComponent(languageCode)}` : null,
    "Não foi possível carregar o dia de hoje.",
  );
}

export function useCurriculumDay(dayId: string | null) {
  return useCurriculumResource<DayDetail>(
    dayId ? `/api/v1/curriculum/day/${dayId}` : null,
    "Não foi possível carregar este dia de estudo.",
  );
}

export async function createCurriculum(
  languageCode: string,
  durationDays: Duration,
): Promise<Curriculum> {
  return api<Curriculum>("/api/v1/curriculum", {
    method: "POST",
    body: { language_code: languageCode, duration_days: durationDays },
  });
}

export async function rescheduleCurriculum(
  curriculumId: string,
  strategy: RescheduleStrategy,
) {
  return api<{ curriculum: Curriculum; strategy: RescheduleStrategy }>(
    `/api/v1/curriculum/${curriculumId}/reschedule`,
    { method: "POST", body: { strategy } },
  );
}

export async function startWeekCheckpoint(curriculumId: string, weekNumber: number) {
  return api<{ placement_test_id: string; week_number: number }>(
    `/api/v1/curriculum/${curriculumId}/checkpoint/${weekNumber}/start`,
    { method: "POST", body: {} },
  );
}
