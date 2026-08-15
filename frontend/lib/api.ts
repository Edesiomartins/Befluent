export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CSRF_STORAGE_KEY = "befluent_csrf_token";

type ApiOptions = Omit<RequestInit, "body"> & { body?: unknown };

export function getCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${name}=`))
    ?.split("=")
    .slice(1)
    .join("=");
}

export function storeCsrfToken(token: string | undefined | null) {
  if (typeof window === "undefined") return;
  if (!token) {
    window.sessionStorage.removeItem(CSRF_STORAGE_KEY);
    return;
  }
  window.sessionStorage.setItem(CSRF_STORAGE_KEY, token);
}

export function clearCsrfToken() {
  storeCsrfToken(null);
}

function resolveCsrfToken(): string | undefined {
  const fromCookie = getCookie("csrf_token");
  if (fromCookie) return decodeURIComponent(fromCookie);
  if (typeof window === "undefined") return undefined;
  return window.sessionStorage.getItem(CSRF_STORAGE_KEY) ?? undefined;
}

async function ensureCsrfToken(): Promise<string | undefined> {
  const existing = resolveCsrfToken();
  if (existing) return existing;
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/csrf`, {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) return undefined;
    const payload = (await response.json()) as { csrf_token?: string };
    if (payload.csrf_token) {
      storeCsrfToken(payload.csrf_token);
      return payload.csrf_token;
    }
  } catch {
    return undefined;
  }
  return undefined;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public retryable?: boolean,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function api<T>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  const hasBody = options.body !== undefined;
  if (hasBody && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = await ensureCsrfToken();
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
    body: hasBody
      ? options.body instanceof FormData
        ? options.body
        : JSON.stringify(options.body)
      : undefined,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      payload?.error?.message ?? "Não foi possível concluir a solicitação.",
      response.status,
      payload?.error?.code,
      payload?.error?.retryable,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
