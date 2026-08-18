"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Input } from "@/components/ui";
import { Logo } from "@/components/logo";
import { AuthHeroHighlights } from "@/components/auth-hero-highlights";
import { BRAND } from "@/lib/brand";

const GENERIC_MESSAGE =
  "Se este e-mail estiver cadastrado, você receberá um link para redefinir sua senha em instantes.";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!email.trim()) return setError("Informe seu e-mail.");
    setLoading(true);
    try {
      await api("/api/v1/auth/forgot-password", {
        method: "POST",
        body: { email: email.trim() },
      });
      setSent(true);
    } catch (caught) {
      // Mesmo em erro inesperado, não confirmamos nem negamos a existência do e-mail.
      if (caught instanceof ApiError && caught.status === 429) {
        setError(caught.message);
      } else {
        setSent(true);
      }
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
              "radial-gradient(circle at 15% 20%, rgba(37,99,235,.55), transparent 42%), radial-gradient(circle at 85% 80%, rgba(219,234,254,.18), transparent 40%)",
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
            Acontece.
            <br />
            Vamos te ajudar a voltar.
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
          <p className="mb-2 text-sm font-semibold text-primary">Recuperar acesso</p>
          <h2 className="page-title">Esqueceu sua senha?</h2>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            Informe o e-mail da sua conta e enviaremos um link para você criar uma nova senha.
          </p>
          {sent ? (
            <p
              className="mt-8 rounded-lg border border-success/25 bg-success/5 p-3 text-sm text-success"
              role="status"
            >
              {GENERIC_MESSAGE}
            </p>
          ) : (
            <form className="mt-8 grid gap-5" onSubmit={submit}>
              <Input
                label="E-mail"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="voce@exemplo.com"
              />
              {error && (
                <p
                  className="rounded-lg border border-danger/25 bg-danger/5 p-3 text-sm text-danger"
                  role="alert"
                >
                  {error}
                </p>
              )}
              <Button type="submit" loading={loading} className="w-full">
                {loading ? "Enviando…" : "Enviar link de redefinição"}
              </Button>
            </form>
          )}
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
