export function DashboardSkeleton() {
  return (
    <div aria-label="Carregando painel" role="status" className="grid gap-8" aria-busy="true">
      <span className="sr-only">Carregando painel</span>
      <div className="flex items-end justify-between gap-8">
        <div className="skeleton h-11 w-2/5" />
        <div className="skeleton hidden h-12 w-2/5 sm:block" />
      </div>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="skeleton h-64 w-full" />
        <div className="skeleton h-64 w-full" />
      </div>
      <div className="skeleton h-36 w-full" />
    </div>
  );
}
