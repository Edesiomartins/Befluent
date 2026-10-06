"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";
import {
  NATIVE_LANGUAGE_CATALOG_UNAVAILABLE,
  NATIVE_LANGUAGE_HELP,
  NATIVE_LANGUAGE_PROMPT,
  loadNativeLanguage,
  loadNativeLanguageChoices,
  rememberNativeLanguage,
  type NativeLanguageOption,
} from "@/lib/native-language";

export function NativeLanguageForm({
  initialCode = "",
  onSaved,
}: {
  initialCode?: string;
  onSaved?: (code: string) => void;
}) {
  const [catalog, setCatalog] = useState<NativeLanguageOption[]>([]);
  const [code, setCode] = useState(initialCode);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [catalogError, setCatalogError] = useState("");

  useEffect(() => {
    let active = true;
    loadNativeLanguage()
      .then(async (state) => {
        if (!active) return;
        const languages = await loadNativeLanguageChoices(state.options);
        if (!active) return;
        setCatalog(languages);
        if (languages.length === 0) setCatalogError(NATIVE_LANGUAGE_CATALOG_UNAVAILABLE);
      })
      .catch((caught) => {
        if (!active) return;
        setCatalogError(
          caught instanceof ApiError ? caught.message : NATIVE_LANGUAGE_CATALOG_UNAVAILABLE,
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function save() {
    if (!code || saving) return;
    setSaving(true);
    setError("");
    try {
      await api("/api/v1/profile", {
        method: "PATCH",
        body: { native_language: code },
      });
      rememberNativeLanguage({ contractActive: true, code, options: [] });
      onSaved?.(code);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível salvar sua língua nativa.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <p className="text-sm text-text-secondary" role="status">
        Carregando línguas nativas…
      </p>
    );
  }

  return (
    <form
      className="grid max-w-xl gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <div>
        <h1 className="page-title">{NATIVE_LANGUAGE_PROMPT}</h1>
        <p className="mt-3 text-sm leading-6 text-text-secondary">{NATIVE_LANGUAGE_HELP}</p>
      </div>
      {catalogError ? (
        <p role="alert" className="text-sm text-danger">
          {catalogError}
        </p>
      ) : (
        <label className="grid gap-2 text-sm font-medium" htmlFor="native-language">
          Língua nativa
          <select
            id="native-language"
            className="min-h-11 rounded-xl border-2 border-border bg-surface px-3"
            value={code}
            onChange={(event) => setCode(event.target.value)}
          >
            <option value="">Escolha</option>
            {catalog.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      <div>
        <Button type="submit" loading={saving} disabled={saving || !code || Boolean(catalogError)}>
          Continuar
        </Button>
      </div>
    </form>
  );
}
