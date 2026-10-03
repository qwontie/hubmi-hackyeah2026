import { env } from "$env/dynamic/public";

const BASE = env.PUBLIC_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

type Json = Record<string, unknown> | unknown[];

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return undefined as T;
  }
  if (res.ok) {
    return (await res.json()) as T;
  }
  let detail = res.statusText;
  try {
    const { detail: parsed } = (await res.json()) as { detail?: string };
    if (parsed) {
      detail = parsed;
    }
  } catch {
    detail = res.statusText;
  }
  throw new ApiError(res.status, detail);
}

async function request<T>(
  method: string,
  path: string,
  body?: Json
): Promise<T> {
  const init: RequestInit = { credentials: "include", method };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, init);
  return handle<T>(res);
}

export const api = {
  del: <T>(path: string) => request<T>("DELETE", path),
  get: <T>(path: string) => request<T>("GET", path),
  patch: <T>(path: string, body?: Json) => request<T>("PATCH", path, body),
  post: <T>(path: string, body?: Json) => request<T>("POST", path, body),
  put: <T>(path: string, body?: Json) => request<T>("PUT", path, body),
};
