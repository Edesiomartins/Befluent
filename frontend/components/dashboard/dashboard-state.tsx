"use client";

import type { ReactNode } from "react";
import { DashboardSkeleton } from "@/components/dashboard-skeleton";

export function DashboardState({
  loading,
  error,
  onRetry,
  children,
}: {
  loading: boolean;
  error: string;
  onRetry: () => void;
  children: ReactNode;
}) {
  if (loading) return <DashboardSkeleton />;
  if (error) {
    return (
      <div>
        <h1 className="page-title">Bem-vindo ao BeFluent</h1>
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}
        </p>
        <button
          type="button"
          className="mt-5 min-h-11 rounded-xl bg-primary px-5 text-sm font-semibold text-white hover:bg-primary-hover"
          onClick={onRetry}
        >
          Tentar novamente
        </button>
      </div>
    );
  }
  return children;
}
