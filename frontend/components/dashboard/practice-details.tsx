import { EmptyState } from "@/components/ui";
import { ModeCard } from "@/components/mode-card";
import { DashboardLink } from "@/components/dashboard/level-block";
import { practiceSlugs, type DashboardData } from "@/components/dashboard/types";
import { getMode } from "@/lib/modes";

export function PracticeDetails({ data }: { data: DashboardData }) {
  const reviews = data.reviews_due ?? [];
  const activity = data.recent_activity ?? [];
  const next = data.next_activity;

  return (
    <div>
      <header>
        <h1 className="page-title">Prática e revisões</h1>
        <p className="mt-2 text-sm text-text-secondary">Fora da missão de hoje.</p>
      </header>

      <section className="panel mt-6 p-6">
        <h2 className="label">Revisões</h2>
        {reviews.length > 0 ? (
          <div className="mt-4 grid gap-3">
            <p className="text-sm text-text-secondary">
              {reviews.length} {reviews.length === 1 ? "revisão pendente" : "revisões pendentes"}.
            </p>
            <ul className="grid gap-2">
              {reviews.slice(0, 3).map((item) => (
                <li key={item.id} className="text-sm text-text-primary">
                  {item.item_type}
                  {typeof item.payload?.term === "string" ? `: ${item.payload.term}` : ""}
                </li>
              ))}
            </ul>
            <DashboardLink href="/learn/review">Abrir revisões</DashboardLink>
          </div>
        ) : (
          <EmptyState
            title="Nenhuma revisão pendente por enquanto."
            description="Itens aparecem aqui quando houver revisão agendada."
            action={<DashboardLink href="/learn/review">Abrir revisões</DashboardLink>}
          />
        )}
      </section>

      <section className="mt-10">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="section-title">Prática livre</h2>
          <DashboardLink href="/learn">Ver todas</DashboardLink>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {practiceSlugs.map((slug) => {
            const mode = getMode(slug);
            if (!mode) return null;
            return <ModeCard key={slug} mode={mode} compact />;
          })}
        </div>
      </section>

      <section className="mt-10">
        <h2 className="section-title">Atividade recente</h2>
        {activity.length > 0 ? (
          <ul className="mt-3 divide-y divide-border border-y border-border">
            {activity.map((session) => (
              <li
                key={session.id}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3 text-sm"
              >
                <span className="font-medium text-text-primary">
                  {session.summary ||
                    (session.status === "completed" ? "Sessão concluída" : "Sessão de estudo")}
                </span>
                <span className="text-text-secondary tabular-nums">
                  {session.started_at
                    ? new Date(session.started_at).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "short",
                      })
                    : null}
                  {typeof session.minutes === "number" ? ` · ${session.minutes} min` : null}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title="Você ainda não iniciou nenhuma prática."
            description="Abra o caminho do dia no cronograma para começar."
            action={
              <DashboardLink href={next?.kind === "curriculum" ? next.href : "/cronograma"}>
                Abrir caminho
              </DashboardLink>
            }
          />
        )}
      </section>
    </div>
  );
}
