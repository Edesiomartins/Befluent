"use client";

import { DashboardState } from "@/components/dashboard/dashboard-state";
import { PracticeDetails } from "@/components/dashboard/practice-details";
import { useDashboard } from "@/components/dashboard/use-dashboard";

export default function DashboardPracticePage() {
  const { data, error, loading, reload } = useDashboard();
  return (
    <DashboardState loading={loading} error={error} onRetry={reload}>
      {data && <PracticeDetails data={data} />}
    </DashboardState>
  );
}
