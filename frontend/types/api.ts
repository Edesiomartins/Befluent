export type LanguageCode =
  | "en"
  | "es-ES"
  | "fr"
  | "it"
  | "de"
  | "ja"
  | "zh-CN"
  | "la";

export type User = {
  id: string;
  name: string;
  email: string;
  is_admin?: boolean;
  /** Presente só quando o backend declara o campo. null = ainda não escolheu. */
  native_language?: string | null;
};

export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
};
