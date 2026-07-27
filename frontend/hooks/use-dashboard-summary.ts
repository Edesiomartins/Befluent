"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Summary = {
  streak_days: number;
  vocabulary_items: number;
};

type DashboardPayload = {
  progress?: {
    streak_days?: number;
    vocabulary_items?: number;
  };
};

/** Lightweight stats for chrome (streak/vocabulary count) — fails silently, chrome has no error UI. */
export function useDashboardSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    let active = true;
    api<DashboardPayload>("/api/v1/dashboard")
      .then((payload) => {
        if (!active) return;
        setSummary({
          streak_days: payload.progress?.streak_days ?? 0,
          vocabulary_items: payload.progress?.vocabulary_items ?? 0,
        });
      })
      .catch(() => {
        if (active) setSummary(null);
      });
    return () => {
      active = false;
    };
  }, []);

  return summary;
}
