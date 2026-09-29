"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { Button, Loading } from "@/components/ui";

type AccountLanguage = {
  code: string;
  name_pt: string;
  source: string;
  status: string;
};

type Account = {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  created_at: string;
  languages: AccountLanguage[];
};

type CatalogLanguage = { code: string; name_pt: string };

const SOURCE_LABEL: Record<string, string> = {
  legacy: "já tinha acesso",
  admin: "liberado aqui",
  trial: "teste",
  promotion: "promoção",
  subscription: "assinatura",
};

function sourceLabel(source: string) {
  return SOURCE_LABEL[source] ?? source;
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("pt-BR");
}

function sameEmail(left: string, right: string) {
  return left.trim().toLocaleLowerCase() === right.trim().toLocaleLowerCase();
}

export default function AdminUsersPage() {
  const [meId, setMeId] = useState("");
  const [users, setUsers] = useState<Account[]>([]);
  const [catalog, setCatalog] = useState<CatalogLanguage[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState("");
  const [grantCode, setGrantCode] = useState<Record<string, string>>({});
  const [deletingId, setDeletingId] = useState("");
  const [confirmEmail, setConfirmEmail] = useState("");

  async function load() {
    const [me, list, languages] = await Promise.all([
      api<{ id: string }>("/api/v1/auth/me"),
      api<{ users: Account[] }>("/api/v1/admin/users"),
      api<CatalogLanguage[]>("/api/v1/languages"),
    ]);
    setMeId(me.id);
    setUsers(list.users);
    setCatalog(languages);
  }

  useEffect(() => {
    let alive = true;
    load()
      .catch((caught) => {
        if (!alive) return;
        setError(caught instanceof ApiError ? caught.message : "Não foi possível carregar os usuários.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const visible = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    if (!term) return users;
    return users.filter(
      (user) =>
        user.name.toLocaleLowerCase().includes(term) ||
        user.email.toLocaleLowerCase().includes(term),
    );
  }, [query, users]);

  async function run(key: string, action: () => Promise<void>) {
    setPending(key);
    setError("");
    try {
      await action();
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Não foi possível concluir a ação.");
    } finally {
      setPending("");
    }
  }

  if (loading) return <Loading label="Carregando usuários" />;

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <div>
        <h1 className="page-title">Usuários</h1>
        <p className="mt-3 leading-7 text-text-secondary">
          Contas do BeFluent. Desativar corta o login na hora. Liberar ou tirar um idioma só registra o direito.
        </p>
      </div>

      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}

      <label className="grid gap-2 text-sm font-medium" htmlFor="admin-user-search">
        Buscar usuário
        <input
          id="admin-user-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Nome ou e-mail"
          className="min-h-11 rounded-[10px] border border-border bg-surface px-3 text-base font-normal"
        />
      </label>

      <div className="grid gap-4">
        {visible.map((user) => {
          const own = user.id === meId;
          const selected = grantCode[user.id] || catalog[0]?.code || "";
          const confirming = deletingId === user.id;
          return (
            <article key={user.id} aria-label={user.email} className="grid gap-4 rounded-[14px] border border-border bg-surface p-4">
              <div>
                <h2 className="text-lg font-semibold">{user.name}</h2>
                <p className="text-sm text-text-secondary">{user.email}</p>
                <p className="mt-1 text-sm">
                  {user.is_active ? "Conta ligada" : "Conta desligada"} · desde {formatDate(user.created_at)}
                </p>
              </div>

              <ul className="grid gap-1 text-sm">
                {user.languages.length === 0 && <li className="text-text-secondary">Nenhum idioma registrado.</li>}
                {user.languages.map((language) => (
                  <li key={`${language.code}-${language.source}`} className="flex flex-wrap items-center justify-between gap-2">
                    <span>
                      {language.name_pt} · {sourceLabel(language.source)}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      disabled={pending !== ""}
                      aria-label={`Tirar ${language.name_pt} de ${user.email}`}
                      onClick={() =>
                        void run(`revoke-${user.id}-${language.code}`, () =>
                          api(`/api/v1/admin/users/${user.id}/languages/${language.code}/revoke`, { method: "POST" }),
                        )
                      }
                    >
                      Tirar
                    </Button>
                  </li>
                ))}
              </ul>
              <p className="text-sm leading-6 text-text-secondary">
                Tirar um idioma cancela o direito. O estudo continua aberto até a regra de acesso por idioma ser ligada.
              </p>

              {catalog.length > 0 && (
                <div className="flex flex-wrap items-end gap-2">
                  <label className="grid gap-1 text-sm font-medium" htmlFor={`grant-${user.id}`}>
                    Liberar idioma
                    <select
                      id={`grant-${user.id}`}
                      value={selected}
                      onChange={(event) => setGrantCode((current) => ({ ...current, [user.id]: event.target.value }))}
                      className="min-h-11 rounded-[10px] border border-border bg-surface px-3"
                    >
                      {catalog.map((language) => (
                        <option key={language.code} value={language.code}>
                          {language.name_pt}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={pending !== "" || !selected}
                    onClick={() =>
                      void run(`grant-${user.id}`, () =>
                        api(`/api/v1/admin/users/${user.id}/languages`, {
                          method: "POST",
                          body: { code: selected },
                        }),
                      )
                    }
                  >
                    Liberar
                  </Button>
                </div>
              )}

              {!own && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={pending !== ""}
                    aria-label={`${user.is_active ? "Desativar" : "Ativar"} ${user.email}`}
                    onClick={() =>
                      void run(`active-${user.id}`, () =>
                        api(`/api/v1/admin/users/${user.id}`, {
                          method: "PATCH",
                          body: { is_active: !user.is_active },
                        }),
                      )
                    }
                  >
                    {user.is_active ? "Desativar" : "Ativar"}
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    disabled={pending !== ""}
                    aria-label={`Apagar ${user.email}`}
                    onClick={() => {
                      setDeletingId(user.id);
                      setConfirmEmail("");
                    }}
                  >
                    Apagar
                  </Button>
                </div>
              )}

              {confirming && (
                <div className="grid gap-3 rounded-[10px] bg-surface-soft p-3">
                  <p className="text-sm leading-6">
                    O login e o progresso desta pessoa somem. O catálogo do app permanece. Digite o e-mail da conta para confirmar.
                  </p>
                  <label className="grid gap-1 text-sm font-medium" htmlFor={`confirm-${user.id}`}>
                    E-mail para confirmar a exclusão
                    <input
                      id={`confirm-${user.id}`}
                      value={confirmEmail}
                      onChange={(event) => setConfirmEmail(event.target.value)}
                      autoComplete="off"
                      className="min-h-11 rounded-[10px] border border-border bg-surface px-3 font-normal"
                    />
                  </label>
                  <Button
                    type="button"
                    variant="danger"
                    aria-label={`Apagar conta de ${user.email}`}
                    disabled={!sameEmail(confirmEmail, user.email) || pending !== ""}
                    onClick={() =>
                      void run(`delete-${user.id}`, async () => {
                        await api(`/api/v1/admin/users/${user.id}`, {
                          method: "DELETE",
                          body: { confirm_email: confirmEmail },
                        });
                        setDeletingId("");
                        setConfirmEmail("");
                      })
                    }
                  >
                    Apagar conta
                  </Button>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
