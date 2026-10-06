import { api, ApiError } from "@/lib/api";

export const NATIVE_LANGUAGE_REQUIRED = "native_language_required";

export const NATIVE_LANGUAGE_PROMPT = "Qual é sua língua nativa?";

export const NATIVE_LANGUAGE_HELP =
  "Usaremos essa língua apenas para explicações e traduções de apoio durante o aprendizado.";

export const NATIVE_LANGUAGE_REQUIRED_MESSAGE =
  "Escolha sua língua nativa para personalizarmos as explicações de apoio.";

export const NATIVE_LANGUAGE_CATALOG_UNAVAILABLE =
  "A lista de línguas nativas ainda não está disponível.";

export type NativeLanguageOption = {
  code: string;
  name: string;
};

export type NativeLanguageState = {
  /** Falso enquanto `/auth/me` não declara o campo. A jornada não é bloqueada. */
  contractActive: boolean;
  code: string | null;
  /** Códigos aceitos, vindos de `native_language_options`. */
  options: string[];
};

/** O contrato acrescenta pt-BR como apoio, sem curso. O catálogo de estudo não traz esse nome. */
const SUPPORT_ONLY_LABELS: Record<string, string> = {
  "pt-BR": "Português (Brasil)",
};

const EXEMPT_PREFIXES = ["/profile", "/admin", "/settings", "/onboarding", "/lingua-nativa"];

let memory: NativeLanguageState | null = null;

export function cachedNativeLanguage(): NativeLanguageState | null {
  return memory;
}

export function rememberNativeLanguage(state: NativeLanguageState) {
  memory = state;
}

export function resetNativeLanguageMemory() {
  memory = null;
}

export function nativeLanguageBlocksPath(pathname: string): boolean {
  return !EXEMPT_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function readNativeLanguage(payload: unknown): NativeLanguageState {
  if (!payload || typeof payload !== "object") {
    return { contractActive: false, code: null, options: [] };
  }
  const record = payload as {
    native_language?: unknown;
    native_language_options?: unknown;
  };
  if (!("native_language" in record) && !("native_language_required" in record)) {
    return { contractActive: false, code: null, options: [] };
  }
  const value = record.native_language;
  const code = typeof value === "string" && value.trim() ? value.trim() : null;
  const options = Array.isArray(record.native_language_options)
    ? record.native_language_options.filter((item): item is string => typeof item === "string" && item.trim() !== "")
    : [];
  return { contractActive: true, code, options };
}

type CatalogLanguage = { code?: string; native_name?: string };

export async function loadNativeLanguageChoices(options: string[]): Promise<NativeLanguageOption[]> {
  let catalog: CatalogLanguage[] = [];
  try {
    const payload = await api<CatalogLanguage[] | { languages?: CatalogLanguage[] }>("/api/v1/languages");
    catalog = Array.isArray(payload) ? payload : [];
  } catch {
    catalog = [];
  }
  return options.map((code) => {
    const known = catalog.find((item) => item.code === code);
    return {
      code,
      name: known?.native_name || SUPPORT_ONLY_LABELS[code] || code,
    };
  });
}

export async function loadNativeLanguage(): Promise<NativeLanguageState> {
  const me = await api<unknown>("/api/v1/auth/me");
  const state = readNativeLanguage(me);
  rememberNativeLanguage(state);
  return state;
}

export function nativeLanguageLabel(
  code: string | null | undefined,
  catalog: NativeLanguageOption[],
): string {
  if (!code) return "";
  return catalog.find((item) => item.code === code)?.name ?? "";
}

export function nativeLanguageRequiredMessage(error: unknown): string | null {
  if (error instanceof ApiError && error.code === NATIVE_LANGUAGE_REQUIRED) {
    return NATIVE_LANGUAGE_REQUIRED_MESSAGE;
  }
  return null;
}
