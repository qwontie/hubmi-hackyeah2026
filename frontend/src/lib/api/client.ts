import { env } from "$env/dynamic/public";

const BASE = (env.PUBLIC_API_BASE_URL ?? "/api").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body: unknown = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  get unauthorized(): boolean {
    return this.status === 401;
  }
}

export type Params = Record<
  string,
  string | number | boolean | null | undefined
>;

function query(params?: Params): string {
  if (!params) {
    return "";
  }
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export function apiUrl(path: string, params?: Params): string {
  const clean = path.startsWith(BASE) ? path : `${BASE}${path}`;
  return `${clean}${query(params)}`;
}

function messageOf(status: number, body: unknown, fallback: string): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    for (const key of ["detail", "error", "message"]) {
      const value = record[key];
      if (typeof value === "string") {
        return value;
      }
      if (value && typeof value === "object" && "message" in value) {
        const nested = (value as { message: unknown }).message;
        if (typeof nested === "string") {
          return nested;
        }
      }
    }
  }
  if (typeof body === "string" && body) {
    return body;
  }
  return fallback || `HTTP ${status}`;
}

async function bodyOf(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function failure(response: Response): Promise<ApiError> {
  const body = await bodyOf(response);
  return new ApiError(
    response.status,
    messageOf(response.status, body, response.statusText),
    body
  );
}

interface RequestOptions {
  body?: unknown;
  form?: FormData;
  params?: Params;
  signal?: AbortSignal;
}

async function request<T>(
  method: string,
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const init: RequestInit = {
    credentials: "include",
    method,
    signal: options.signal,
  };
  if (options.form) {
    init.body = options.form;
  } else if (options.body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(apiUrl(path, options.params), init);
  if (!response.ok) {
    throw await failure(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  del: <T = void>(path: string, params?: Params) =>
    request<T>("DELETE", path, { params }),
  get: <T>(path: string, params?: Params, signal?: AbortSignal) =>
    request<T>("GET", path, { params, signal }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>("PATCH", path, { body: body ?? {} }),
  post: <T>(path: string, body?: unknown) =>
    request<T>("POST", path, { body: body ?? {} }),
  put: <T>(path: string, body?: unknown) =>
    request<T>("PUT", path, { body: body ?? {} }),
  upload: <T>(path: string, form: FormData) =>
    request<T>("PUT", path, { form }),
  url: apiUrl,
};
