"use client";

import { DashboardState } from "@/components/dashboard/dashboard-state";
import { HomeFocus } from "@/components/dashboard/home-focus";
import { useDashboard } from "@/components/dashboard/use-dashboard";

export default function DashboardPage() {
  const { data, error, loading, today, reload } = useDashboard();
  return (
    <DashboardState loading={loading} error={error} onRetry={reload}>
      {data && <HomeFocus data={data} today={today} />}
    </DashboardState>
  );
}
