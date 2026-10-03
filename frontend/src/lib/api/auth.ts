import { api } from "$lib/api/client";

export interface Me {
  login: string;
}

export const login = (user: string, password: string) =>
  api.post<Me>("/auth/login", { login: user, password });

export const logout = () => api.post<void>("/auth/logout");

export const me = () => api.get<Me>("/auth/me");
