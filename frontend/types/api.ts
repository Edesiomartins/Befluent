export type LanguageCode =
  | "en"
  | "es-ES"
  | "fr"
  | "ja"
  | "zh-CN"
  | "la"
  | "la-classical";

export type User = {
  id: string;
  name: string;
  email: string;
};

export type ApiErrorPayload = {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
};
