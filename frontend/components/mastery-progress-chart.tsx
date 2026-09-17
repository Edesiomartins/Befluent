export type MasteryTimelinePoint = {
  date: string;
  percent: number | null;
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

function shortDate(iso: string) {
  return localDate(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).replace(".", "");
}

function pointGroups(timeline: MasteryTimelinePoint[]) {
  const groups: Array<Array<{ x: number; y: number }>> = [];
  let group: Array<{ x: number; y: number }> = [];
  const width = 100;
  const height = 64;

  timeline.forEach((point, index) => {
    if (typeof point.percent !== "number") {
      if (group.length > 0) groups.push(group);
      group = [];
      return;
    }
    const x = timeline.length === 1 ? width / 2 : (index / (timeline.length - 1)) * width;
    group.push({ x, y: height - (point.percent / 100) * height });
  });
  if (group.length > 0) groups.push(group);
  return groups;
}

export function MasteryProgressChart({ timeline }: { timeline?: MasteryTimelinePoint[] }) {
  const points = timeline ?? [];
  const groups = pointGroups(points);
  const knownPoints = groups.flat();

  if (knownPoints.length === 0) {
    return <p className="mt-5 text-sm text-text-secondary">Dados em calibração: ainda não há histórico de domínio suficiente.</p>;
  }

  return (
    <figure className="mt-5">
      <figcaption className="text-sm text-text-secondary">
        A curva mostra somente evidências demonstradas em cada dia.
      </figcaption>
      <div className="mt-4 overflow-x-auto">
        <svg className="h-44 min-w-[20rem] w-full" viewBox="0 0 100 80" preserveAspectRatio="none" role="img" aria-labelledby="mastery-chart-title" aria-describedby="mastery-chart-description">
          <title id="mastery-chart-title">Evolução do domínio demonstrado</title>
          <desc id="mastery-chart-description">Percentual de domínio demonstrado nos dias com evidência disponível.</desc>
          <line x1="0" x2="100" y1="64" y2="64" className="stroke-border" strokeWidth="0.5" />
          <line x1="0" x2="100" y1="32" y2="32" className="stroke-border" strokeWidth="0.3" strokeDasharray="2 2" />
          {groups.map((group, index) => group.length > 1 && (
            <polyline key={index} points={group.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" className="stroke-primary" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
          ))}
          {knownPoints.map((point, index) => (
            <circle key={index} cx={point.x} cy={point.y} r="1.5" className="fill-primary" vectorEffect="non-scaling-stroke" />
          ))}
          {points.map((point, index) => (
            <text key={point.date} x={points.length === 1 ? 50 : (index / (points.length - 1)) * 100} y="77" textAnchor="middle" className="fill-text-secondary" fontSize="5">{shortDate(point.date)}</text>
          ))}
        </svg>
      </div>
      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-semibold text-primary">Ver dados</summary>
        <div className="mt-3 max-h-64 overflow-auto rounded-xl border border-border">
          <table className="w-full text-left" aria-label="Domínio por dia">
            <thead className="sticky top-0 bg-surface-soft"><tr><th className="px-3 py-2">Data</th><th className="px-3 py-2">Domínio demonstrado</th></tr></thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.date} className="border-t border-border"><td className="px-3 py-2">{longDate(point.date)}</td><td className="px-3 py-2">{typeof point.percent === "number" ? `${point.percent}%` : "Sem evidência"}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
