export function DashboardSkeleton() {
  return (
    <div aria-label="Carregando painel" role="status" className="grid gap-5">
      <span className="sr-only">Carregando painel</span>
      <div className="skeleton h-10 w-2/5" />
      <div className="skeleton h-48 w-full" />
      <div className="skeleton h-28 w-full" />
    </div>
  );
}
