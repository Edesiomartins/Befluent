import { api } from "@/lib/api";
import type { User } from "@/types/api";

export const authService = {
  login: (email: string, password: string) =>
    api<User>("/api/v1/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  me: () => api<User>("/api/v1/auth/me"),
  logout: () => api<void>("/api/v1/auth/logout", { method: "POST" }),
};
