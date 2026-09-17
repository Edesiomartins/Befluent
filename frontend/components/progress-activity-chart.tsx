export type DailyActivity = {
  period_start: string;
  period_end: string;
  timezone: string;
  total_minutes: number;
  days: Array<{ date: string; minutes: number | null }>;
};

function localDate(iso: string) {
  return new Date(`${iso}T12:00:00Z`);
}

function longDate(iso: string) {
  return localDate(iso).toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function shortDay(iso: string) {
  return localDate(iso)
    .toLocaleDateString("pt-BR", { weekday: "short", timeZone: "UTC" })
    .replace(".", "");
}

function periodLabel(start: string, end: string) {
  const startDate = localDate(start);
  const endDate = localDate(end);
  const sameMonth = startDate.getUTCMonth() === endDate.getUTCMonth();
  const sameYear = startDate.getUTCFullYear() === endDate.getUTCFullYear();
  if (sameMonth && sameYear) {
    return `${startDate.getUTCDate()} a ${longDate(end)}`;
  }
  return `${longDate(start)} a ${longDate(end)}`;
}

export function ProgressActivityChart({ activity }: { activity?: DailyActivity }) {
  if (!activity) {
    return <p className="mt-5 text-sm text-text-secondary">Histórico diário indisponível.</p>;
  }

  if (activity.days.length === 0) {
    return <p className="mt-5 text-sm text-text-secondary">Ainda não há dados diários neste período.</p>;
  }

  const knownMinutes = activity.days.flatMap((day) =>
    typeof day.minutes === "number" ? [day.minutes] : [],
  );
  const maximum = Math.max(1, ...knownMinutes);

  return (
    <figure className="mt-5">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-2">
        <span>
          <span className="text-sm font-medium text-text-primary">
            {periodLabel(activity.period_start, activity.period_end)}
          </span>
          <span className="ml-3 text-sm text-text-secondary">{activity.total_minutes} min no período</span>
        </span>
        <span className="text-xs text-text-secondary">Fuso: {activity.timezone}</span>
      </figcaption>

      <div className="mt-6 overflow-x-auto pb-2" aria-hidden="true">
        <div className={activity.days.length > 7 ? "min-w-[42rem]" : "min-w-[20rem]"}>
          <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${activity.days.length}, minmax(0, 1fr))` }}>
            {activity.days.map((day) => <span key={day.date} className="text-center text-xs tabular-nums text-text-secondary">{day.minutes ?? "—"}</span>)}
          </div>
          <div className="mt-2 grid h-36 items-end gap-2 border-b border-border" style={{ gridTemplateColumns: `repeat(${activity.days.length}, minmax(0, 1fr))` }}>
            {activity.days.map((day) => {
              const minutes = day.minutes;
              const known = typeof minutes === "number";
              const height = known ? (minutes / maximum) * 100 : 100;
              return <span key={day.date} className="flex h-full items-end"><span className={known ? (minutes === 0 ? "h-px w-full bg-border" : "w-full rounded-t bg-primary") : "h-full w-full rounded-t border border-dashed border-border bg-surface-soft"} style={known && minutes > 0 ? { height: `${height}%` } : undefined} /></span>;
            })}
          </div>
          <div className="mt-2 grid gap-2" style={{ gridTemplateColumns: `repeat(${activity.days.length}, minmax(0, 1fr))` }}>
            {activity.days.map((day) => <span key={day.date} className="text-center text-xs capitalize text-text-secondary">{activity.days.length > 7 ? localDate(day.date).getUTCDate() : shortDay(day.date)}</span>)}
          </div>
        </div>
      </div>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-semibold text-primary">Ver dados</summary>
        <div className="mt-3 max-h-64 overflow-auto rounded-xl border border-border">
          <table className="w-full text-left" aria-label="Minutos estudados por dia">
            <thead className="sticky top-0 bg-surface-soft"><tr><th className="px-3 py-2">Data</th><th className="px-3 py-2">Tempo</th></tr></thead>
            <tbody>
              {activity.days.map((day) => (
                <tr key={day.date} className="border-t border-border"><td className="px-3 py-2">{longDate(day.date)}</td><td className="px-3 py-2">{typeof day.minutes === "number" ? `${day.minutes} min` : "Sem dado"}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
