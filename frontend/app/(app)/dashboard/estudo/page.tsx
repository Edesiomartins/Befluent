"use client";

import { DashboardState } from "@/components/dashboard/dashboard-state";
import { StudyDetails } from "@/components/dashboard/study-details";
import { useDashboard } from "@/components/dashboard/use-dashboard";

export default function DashboardStudyPage() {
  const { data, error, loading, today, reload } = useDashboard();
  return (
    <DashboardState loading={loading} error={error} onRetry={reload}>
      {data && <StudyDetails data={data} today={today} />}
    </DashboardState>
  );
}
