"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { Button, EmptyState, Loading } from "@/components/ui";
import { levelShortCode } from "@/lib/levels";

type CatalogLanguage = {
  id: string;
  code: string;
  name_pt: string;
  native_name: string;
  description?: string;
};

type MineLanguage = CatalogLanguage & {
  user_language_id: string;
  active: boolean;
  level_estimate: string | null;
  current_level: string | null;
  onboarding_completed: boolean;
};

export default function LanguagesPage() {
  const [catalog, setCatalog] = useState<CatalogLanguage[]>([]);
  const [mine, setMine] = useState<MineLanguage[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");

  async function load() {
    setError("");
    const [all, owned] = await Promise.all([
      api<CatalogLanguage[]>("/api/v1/languages"),
      api<MineLanguage[]>("/api/v1/languages/mine"),
    ]);
    setCatalog(all);
    setMine(owned);
  }

  useEffect(() => {
    let active = true;
    load()
      .catch((caught) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.message
            : "Não foi possível carregar os idiomas.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function activate(code: string) {
    setSaving(code);
    setError("");
    try {
      await api("/api/v1/languages/activate", {
        method: "POST",
        body: { code },
      });
      await load();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível ativar o idioma.",
      );
    } finally {
      setSaving("");
    }
  }

  if (loading) return <Loading label="Carregando idiomas" />;

  const mineByCode = new Map(mine.map((item) => [item.code, item]));
  const activeCode = mine.find((item) => item.active)?.code ?? null;

  return (
    <div>
      <p className="text-sm font-semibold text-primary">Catálogo de estudo</p>
      <h1 className="mt-2 page-title">Idiomas</h1>
      <p className="mt-3 max-w-2xl leading-7 text-text-secondary">
        Escolha o foco da sua próxima sessão. Seu progresso fica separado por idioma.
      </p>

      {error && (
        <p role="alert" className="mt-6 text-sm text-danger">
          {error}
        </p>
      )}

      {catalog.length === 0 ? (
        <div className="mt-9">
          <EmptyState
            title="Nenhum idioma disponível."
            description="Tente novamente em instantes."
            action={
              <Button variant="secondary" onClick={() => void load().catch(() => undefined)}>
                Recarregar
              </Button>
            }
          />
        </div>
      ) : (
        <div className="mt-9 grid gap-3">
          {catalog.map((language) => {
            const owned = mineByCode.get(language.code);
            const isActive = activeCode === language.code;
            const level =
              levelShortCode(owned?.current_level) ||
              owned?.level_estimate ||
              null;
            const status = isActive
              ? "Idioma ativo"
              : owned?.onboarding_completed
                ? "Em andamento"
                : owned
                  ? "Configurado"
                  : "Novo";

            return (
              <article
                key={language.code}
                className={`panel grid gap-4 p-5 transition sm:grid-cols-[1fr_auto] sm:items-center ${
                  isActive ? "border-primary" : ""
                }`}
              >
                <div className="flex items-center gap-4">
                  <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary-soft text-sm font-bold text-primary">
                    {language.code.toUpperCase().slice(0, 2)}
                  </span>
                  <div>
                    <h2 className="font-semibold">
                      {language.name_pt}{" "}
                      <span className="ml-2 font-normal text-text-secondary">
                        {language.native_name}
                      </span>
                    </h2>
                    <p className="mt-1 text-sm text-text-secondary">
                      {status}
                      {level ? ` · Nível ${level}` : ""}
                    </p>
                  </div>
                </div>
                {isActive ? (
                  <div className="flex flex-col items-start gap-2 sm:items-end">
                    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-success">
                      <span className="size-2 rounded-full bg-success" aria-hidden />
                      Ativo
                    </span>
                    {!owned?.onboarding_completed && (
                      <Link
                        href="/onboarding"
                        className="text-sm font-semibold text-primary hover:underline"
                      >
                        Completar plano
                      </Link>
                    )}
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    loading={saving === language.code}
                    onClick={() => void activate(language.code)}
                  >
                    Estudar este idioma
                  </Button>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
