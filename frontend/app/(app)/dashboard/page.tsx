import Link from "next/link";
import { EmptyState } from "@/components/ui";

export default function DashboardPage() {
  return (
    <div>
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-sm font-semibold text-primary">Painel</p>
          <h1 className="page-title">Bem-vindo ao BeFluent</h1>
          <p className="mt-3 text-text-secondary">
            Organize sua rotina de estudo e avance no seu ritmo.
          </p>
        </div>
        <Link
          href="/learn"
          className="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--primary-hover)]"
        >
          Ir para prática
        </Link>
      </div>

      <section className="mt-9 grid gap-5 md:grid-cols-2">
        <article className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Idioma ativo
          </p>
          <EmptyState
            title="Escolha um idioma para começar."
            description="Defina o idioma principal no onboarding ou na área de idiomas."
            action={
              <Link href="/languages" className="text-sm font-semibold text-primary hover:underline">
                Ver idiomas
              </Link>
            }
          />
        </article>
        <article className="panel p-5">
          <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
            Revisões
          </p>
          <EmptyState
            title="Nenhuma revisão pendente por enquanto."
            description="Quando você salvar vocabulário ou completar práticas, as revisões aparecerão aqui."
            action={
              <Link href="/learn/review" className="text-sm font-semibold text-primary hover:underline">
                Abrir revisões
              </Link>
            }
          />
        </article>
      </section>

      <section className="mt-5 panel p-5">
        <p className="text-xs font-semibold uppercase tracking-[.12em] text-text-secondary">
          Atividade recente
        </p>
        <EmptyState
          title="Você ainda não iniciou nenhuma prática."
          description="Comece por conversação, vocabulário ou uma aula guiada."
          action={
            <div className="flex flex-wrap gap-3">
              <Link
                href="/learn/conversation"
                className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-[var(--primary-hover)]"
              >
                Conversação
              </Link>
              <Link
                href="/onboarding"
                className="rounded-lg border border-border px-4 py-2 text-sm font-semibold text-text-primary hover:bg-surface-elevated"
              >
                Configurar plano
              </Link>
            </div>
          }
        />
      </section>
    </div>
  );
}
