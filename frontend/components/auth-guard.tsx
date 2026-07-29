"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);
  const [backendError, setBackendError] = useState("");
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let active = true;
    setChecking(true);
    setBackendError("");

    (async () => {
      try {
        await api("/api/v1/auth/me");
      } catch (error) {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace(`/login?retorno=${encodeURIComponent(pathname)}`);
          return;
        }
        setBackendError(
          error instanceof ApiError
            ? error.message
            : "Não foi possível validar sua sessão. Verifique a conexão e tente novamente.",
        );
        setChecking(false);
        return;
      }

      if (pathname !== "/onboarding") {
        try {
          const status = await api<{ completed: boolean }>("/api/v1/onboarding/status");
          if (!status.completed) {
            router.replace("/onboarding");
            return;
          }
        } catch (error) {
          if (!active) return;
          if (error instanceof ApiError && error.status === 401) {
            router.replace(`/login?retorno=${encodeURIComponent(pathname)}`);
            return;
          }
          setBackendError(
            error instanceof ApiError
              ? error.message
              : "Não foi possível verificar o onboarding.",
          );
          setChecking(false);
          return;
        }
      }

      if (active) setChecking(false);
    })();

    return () => {
      active = false;
    };
  }, [pathname, router, retryToken]);

  if (checking) {
    return (
      <div
        className="grid min-h-screen place-items-center text-sm text-text-secondary"
        role="status"
      >
        Verificando sua sessão…
      </div>
    );
  }

  if (backendError) {
    return (
      <div className="grid min-h-screen place-items-center px-5">
        <div className="max-w-md rounded-2xl border border-danger/25 bg-danger/5 p-6 text-center" role="alert">
          <h1 className="text-lg font-semibold text-danger">Sessão indisponível</h1>
          <p className="mt-2 text-sm text-text-secondary">{backendError}</p>
          <div className="mt-5 flex flex-wrap justify-center gap-3">
            <Button variant="secondary" onClick={() => setRetryToken((value) => value + 1)}>
              Tentar novamente
            </Button>
            <Button onClick={() => router.replace("/login")}>Ir para o login</Button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
