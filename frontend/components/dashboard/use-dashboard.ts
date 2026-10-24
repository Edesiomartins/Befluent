"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useActiveLanguage } from "@/hooks/use-active-language";
import { useTodayInCurriculum } from "@/hooks/use-curriculum";
import type { TodayPayload } from "@/types/curriculum";
import type { DashboardData } from "@/components/dashboard/types";

export function useDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const { code, resolved } = useActiveLanguage();
  const todayResource = useTodayInCurriculum(resolved ? code : null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<DashboardData>("/api/v1/dashboard")
      .then((payload) => {
        if (active) setData(payload);
      })
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar o painel.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const today: TodayPayload | null =
    todayResource.status === "ready" && todayResource.data?.day ? todayResource.data : null;

  return {
    data,
    error,
    loading,
    code,
    today,
    reload: () => setReloadKey((key) => key + 1),
  };
}
