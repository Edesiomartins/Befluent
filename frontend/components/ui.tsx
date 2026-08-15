import {
  forwardRef,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { AlertTriangle, Eye, EyeOff } from "lucide-react";
import { ApiError } from "@/lib/api";
import { useCooldown } from "@/hooks/use-cooldown";

/** Cooldown do circuit breaker de IA no backend (`provider_resilience.py`). */
const AI_RETRY_COOLDOWN_SECONDS = 30;

export function isAiUnavailableError(error: unknown): error is ApiError {
  return error instanceof ApiError && (error.code === "ai_unavailable" || error.status === 503);
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "success" | "danger" | "ghost";
  loading?: boolean;
};

export function Button({
  variant = "primary",
  loading,
  className = "",
  children,
  disabled,
  ...props
}: ButtonProps) {
  const styles = {
    primary:
      "bg-primary text-white shadow-[0_4px_0_var(--primary-shadow)] hover:bg-[var(--primary-hover)] active:translate-y-[3px] active:shadow-[0_1px_0_var(--primary-shadow)]",
    secondary:
      "border-2 border-border bg-surface text-text-primary shadow-[0_4px_0_var(--secondary-shadow)] hover:bg-surface-elevated active:translate-y-[3px] active:shadow-[0_1px_0_var(--secondary-shadow)]",
    success:
      "bg-success text-white shadow-[0_4px_0_var(--success-shadow)] hover:opacity-95 active:translate-y-[3px] active:shadow-[0_1px_0_var(--success-shadow)]",
    danger:
      "bg-danger text-white shadow-[0_4px_0_var(--danger-shadow)] hover:opacity-95 active:translate-y-[3px] active:shadow-[0_1px_0_var(--danger-shadow)]",
    ghost: "text-text-secondary hover:bg-surface-elevated hover:text-text-primary",
  };
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-bold transition-[transform,box-shadow,background-color] duration-100 disabled:cursor-not-allowed disabled:opacity-55 disabled:active:translate-y-0 disabled:active:shadow-[0_4px_0_var(--secondary-shadow)] ${styles[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <span className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden />}
      {children}
    </button>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, id, className = "", ...props },
  ref,
) {
  const inputId = id ?? props.name;
  return (
    <label className="grid gap-2 text-sm font-medium" htmlFor={inputId}>
      {label}
      <input
        ref={ref}
        id={inputId}
        className={`min-h-11 rounded-xl border-2 bg-surface px-3.5 py-2.5 text-text-primary placeholder:text-text-secondary/65 focus:border-primary ${error ? "border-danger" : "border-border"} ${className}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      {error && <span id={`${inputId}-error`} className="text-sm font-normal text-danger">{error}</span>}
    </label>
  );
});

type PasswordInputProps = Omit<InputProps, "type">;

/** Campo de senha com botão de olho para mostrar/ocultar. */
export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  function PasswordInput({ label, error, id, className = "", ...props }, ref) {
    const [visible, setVisible] = useState(false);
    const inputId = id ?? props.name;
    const toggleLabel = visible ? "Ocultar senha" : "Mostrar senha";

    return (
      <div className="grid gap-2 text-sm font-medium">
        <label htmlFor={inputId}>{label}</label>
        <div className="relative">
          <input
            ref={ref}
            id={inputId}
            type={visible ? "text" : "password"}
            className={`min-h-11 w-full rounded-xl border-2 bg-surface py-2.5 pl-3.5 pr-12 text-text-primary placeholder:text-text-secondary/65 focus:border-primary ${error ? "border-danger" : "border-border"} ${className}`}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? `${inputId}-error` : undefined}
            {...props}
          />
          <button
            type="button"
            className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-xl text-text-secondary transition hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            onClick={() => setVisible((value) => !value)}
            aria-label={toggleLabel}
            aria-pressed={visible}
            title={toggleLabel}
          >
            {visible ? (
              <EyeOff className="size-5" aria-hidden />
            ) : (
              <Eye className="size-5" aria-hidden />
            )}
          </button>
        </div>
        {error && (
          <span id={`${inputId}-error`} className="text-sm font-normal text-danger">
            {error}
          </span>
        )}
      </div>
    );
  },
);

export function Loading({ label = "Carregando" }: { label?: string }) {
  return (
    <div className="grid gap-4" aria-label={label} role="status">
      <span className="sr-only">{label}</span>
      <div className="skeleton h-8 w-2/5" />
      <div className="skeleton h-24 w-full" />
      <div className="skeleton h-16 w-4/5" />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="mt-4 grid justify-items-start gap-2">
      <h2 className="section-title">{title}</h2>
      <p className="max-w-lg text-sm leading-6 text-text-secondary">{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  retry,
  message = "Não foi possível carregar este conteúdo.",
  error,
}: {
  retry?: () => void;
  message?: string;
  /** Erro original, se veio de `api()`. Detecta indisponibilidade de IA para
   * mostrar o cooldown real em vez de um botão que falha na hora. */
  error?: unknown;
}) {
  const aiUnavailable = isAiUnavailableError(error);
  const remaining = useCooldown(AI_RETRY_COOLDOWN_SECONDS, error, aiUnavailable);
  const waiting = aiUnavailable && remaining > 0;

  return (
    <div className="rounded-2xl border border-danger/25 bg-danger/5 p-5" role="alert">
      <h2 className="flex items-center gap-2 font-semibold text-danger">
        <AlertTriangle className="size-5 shrink-0" aria-hidden />
        {aiUnavailable ? "IA temporariamente indisponível" : "Algo não saiu como esperado"}
      </h2>
      <p className="mt-1 text-sm text-text-secondary">
        {aiUnavailable
          ? "O provedor de IA está sobrecarregado ou indisponível no momento. Isso costuma se resolver sozinho em pouco tempo."
          : message}
      </p>
      {retry && (
        <Button
          variant="secondary"
          className="mt-4"
          onClick={retry}
          disabled={waiting}
        >
          {waiting ? `Tentar novamente em ${remaining}s` : "Tentar novamente"}
        </Button>
      )}
    </div>
  );
}

export function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-5 border-b border-border py-4 last:border-0">
      <span><span className="block text-sm font-medium">{label}</span>{description && <span className="mt-1 block text-sm text-text-secondary">{description}</span>}</span>
      <input className="sr-only" type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span
        aria-hidden
        className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors ${checked ? "bg-success" : "bg-border"}`}
      >
        <span
          className={`inline-block size-5 transform rounded-full bg-white shadow transition-transform ${checked ? "translate-x-6" : "translate-x-1"}`}
        />
      </span>
    </label>
  );
}
