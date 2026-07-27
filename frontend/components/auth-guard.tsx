"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);
  const [demo, setDemo] = useState(false);

  useEffect(() => {
    let active = true;
    api("/api/v1/auth/me")
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) {
          router.replace(`/login?retorno=${encodeURIComponent(pathname)}`);
          return;
        }
        if (active) setDemo(true);
      })
      .finally(() => active && setChecking(false));
    return () => { active = false; };
  }, [pathname, router]);

  if (checking) {
    return <div className="grid min-h-screen place-items-center text-sm text-text-secondary" role="status">Verificando sua sessão…</div>;
  }
  return (
    <>
      {demo && <div className="bg-info px-4 py-2 text-center text-xs font-medium text-white">Backend indisponível — exibindo dados de demonstração.</div>}
      {children}
    </>
  );
}
