"use client";

import Link from "next/link";
import { FormEvent, Suspense, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Button, PasswordInput } from "@/components/ui";
import { Logo } from "@/components/logo";
import { AuthHeroHighlights } from "@/components/auth-hero-highlights";
import { BRAND } from "@/lib/brand";

function PasswordHints({ password }: { password: string }) {
  const checks = [
    { ok: password.length >= 8, label: "Pelo menos 8 caracteres" },
    { ok: /[A-Za-z]/.test(password), label: "Contém letras" },
    { ok: /\d/.test(password) || password.length >= 10, label: "Números ou senha mais longa" },
  ];
  return (
    <ul className="grid gap-1 text-xs text-text-secondary" aria-live="polite">
      {checks.map((item) => (
        <li key={item.label} className={item.ok ? "text-success" : undefined}>
          {item.ok ? "✓" : "•"} {item.label}
        </li>
      ))}
    </ul>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (!token) {
      setError("Link inválido. Solicite uma nova redefinição de senha.");
      return;
    }
    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      passwordRef.current?.focus();
      return;
    }
    if (password !== passwordConfirmation) {
      setError("As senhas não coincidem.");
      confirmRef.current?.focus();
      return;
    }

    setLoading(true);
    try {
      await api("/api/v1/auth/reset-password", {
        method: "POST",
        body: { token, password, password_confirmation: passwordConfirmation },
      });
      setSuccess(true);
      window.setTimeout(() => {
        router.replace("/login");
      }, 1200);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Não foi possível redefinir a senha. Tente novamente.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      <section className="relative hidden overflow-hidden bg-[var(--primary-deep)] px-14 py-12 text-white lg:flex lg:flex-col">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          aria-hidden
          style={{
            background:
              "radial-gradient(circle at 20% 15%, rgba(37,99,235,.5), transparent 40%), radial-gradient(circle at 80% 70%, rgba(219,234,254,.16), transparent 38%)",
          }}
        />
        <div className="relative">
          <Logo variant="light" />
        </div>
        <div className="relative my-auto max-w-xl">
          <p className="mb-6 text-sm font-semibold uppercase tracking-[.18em] text-white/55">
            {BRAND.slogan}
          </p>
          <h1 className="text-5xl font-semibold leading-[1.08] tracking-[-.045em]">
            Nova senha,
            <br />
            de volta ao ritmo.
          </h1>
          <p className="mt-7 max-w-md text-lg leading-8 text-white/70">
            {BRAND.description}
          </p>
          <AuthHeroHighlights />
        </div>
        <p className="relative text-sm text-white/45">{BRAND.institutional}</p>
      </section>
      <section className="flex items-center justify-center bg-surface px-5 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10 lg:hidden">
            <Logo />
          </div>
          <p className="mb-2 text-sm font-semibold text-primary">Redefinir senha</p>
          <h2 className="page-title">Escolha uma nova senha</h2>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            Defina uma nova senha para voltar a acessar sua conta.
          </p>
          {!token && (
            <p
              className="mt-5 rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger"
              role="alert"
            >
              Link inválido. Solicite uma nova redefinição.
            </p>
          )}
          <form className="mt-8 grid gap-5" onSubmit={submit} autoComplete="off">
            <div className="grid gap-2">
              <PasswordInput
                ref={passwordRef}
                label="Nova senha"
                name="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={success}
              />
              <PasswordHints password={password} />
            </div>
            <PasswordInput
              ref={confirmRef}
              label="Confirmar nova senha"
              name="password_confirmation"
              autoComplete="new-password"
              value={passwordConfirmation}
              onChange={(e) => setPasswordConfirmation(e.target.value)}
              disabled={success}
            />
            {error && (
              <p
                className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger"
                role="alert"
              >
                {error}
              </p>
            )}
            {success && (
              <p
                className="rounded-lg border border-success/25 bg-success/5 p-3 text-sm text-success"
                role="status"
              >
                Senha redefinida com sucesso. Redirecionando para o login...
              </p>
            )}
            <Button type="submit" loading={loading} className="w-full" disabled={success || !token}>
              {loading ? "Salvando…" : "Salvar nova senha"}
            </Button>
          </form>
          <p className="mt-6 text-center text-sm text-text-secondary">
            Lembrou a senha?{" "}
            <Link
              href="/login"
              className="font-semibold text-primary underline-offset-2 hover:underline"
            >
              Voltar para o login
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center text-sm text-text-secondary">
          Carregando…
        </main>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
