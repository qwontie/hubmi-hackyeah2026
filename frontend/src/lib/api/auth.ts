import { api } from "$lib/api/client";

export interface Me {
  display_name?: string | null;
  expertise?: string | null;
  login: string;
  role?: "admin" | "expert";
}

export const login = (user: string, password: string) =>
  api.post<Me>("/auth/login", { login: user, password });

export const logout = () => api.post<void>("/auth/logout");

export const me = () => api.get<Me>("/auth/me");
