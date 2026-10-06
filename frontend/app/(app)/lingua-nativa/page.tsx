"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { NativeLanguageForm } from "@/components/native-language-form";

function NativeLanguagePage() {
  const router = useRouter();
  const search = useSearchParams();
  const raw = search.get("retorno") || "/dashboard";
  const next = raw.startsWith("/") && !raw.startsWith("//") ? raw : "/dashboard";

  return (
    <NativeLanguageForm
      onSaved={() => {
        router.replace(next.startsWith("/") ? next : "/dashboard");
      }}
    />
  );
}

export default function Page() {
  return (
    <Suspense fallback={<p className="text-sm text-text-secondary">Carregando…</p>}>
      <NativeLanguagePage />
    </Suspense>
  );
}
