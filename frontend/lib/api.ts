export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
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
    const csrfToken = getCookie("csrf_token");
    if (csrfToken) headers.set("X-CSRF-Token", decodeURIComponent(csrfToken));
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
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
