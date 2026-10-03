import { API_BASE } from "@/config";
import type {
  Category,
  ErrorCode,
  FieldError,
  InnovationDetail,
  InnovationSummary,
  MatchRequest,
  MatchResponse,
  NeedPatch,
  NeedPatchResponse,
  Page,
  Powiat,
} from "./types";

const FALLBACK_MESSAGES: Record<ErrorCode, string> = {
  ai_unavailable:
    "Wyszukiwanie jest chwilowo niedostępne. Spróbuj ponownie za kilka minut.",
  bad_request: "Nie udało się wysłać zapytania. Spróbuj ponownie.",
  conflict: "Ta operacja właśnie trwa. Spróbuj za chwilę.",
  internal: "Coś poszło nie tak po naszej stronie. Spróbuj ponownie.",
  network:
    "Nie możemy połączyć się z serwerem. Sprawdź internet i spróbuj ponownie.",
  not_found: "Nie znaleźliśmy tej strony.",
  rate_limited: "Za dużo zapytań w krótkim czasie. Spróbuj za chwilę.",
  text_too_long: "Opis jest za długi. Skróć go do 2000 znaków.",
  text_too_short: "Opisz problem w co najmniej 10 znakach.",
  unauthorized: "Brak dostępu.",
  unclear_text:
    "Nie rozumiemy tego opisu. Napisz zwykłymi słowami, z jakim problemem przychodzisz.",
  validation_error: "Popraw zaznaczone pola.",
};

interface ApiErrorOptions {
  cause?: unknown;
  code: ErrorCode;
  fields?: FieldError[];
  retryAfter?: number | null;
  status: number;
}

export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;
  readonly fields: FieldError[];
  readonly retryAfter: number | null;

  constructor(message: string, options: ApiErrorOptions) {
    super(message, { cause: options.cause });
    this.code = options.code;
    this.status = options.status;
    this.fields = options.fields ?? [];
    this.retryAfter = options.retryAfter ?? null;
  }
}

const codeFromStatus = (status: number): ErrorCode => {
  if (status === 404) {
    return "not_found";
  }
  if (status === 429) {
    return "rate_limited";
  }
  if (status === 503) {
    return "ai_unavailable";
  }
  if (status === 422) {
    return "validation_error";
  }
  if (status >= 400 && status < 500) {
    return "bad_request";
  }
  return "internal";
};

const isErrorCode = (value: unknown): value is ErrorCode =>
  typeof value === "string" && value in FALLBACK_MESSAGES;

const toApiError = async (response: Response): Promise<ApiError> => {
  const retryHeader = response.headers.get("retry-after");
  const retryAfter = retryHeader ? Number.parseInt(retryHeader, 10) : null;
  let code = codeFromStatus(response.status);
  let message = FALLBACK_MESSAGES[code];
  let fields: FieldError[] = [];
  try {
    const body = (await response.json()) as { detail?: unknown };
    const { detail } = body;
    if (typeof detail === "string" && detail.length > 0) {
      message = detail;
    } else if (detail && typeof detail === "object") {
      const {
        code: rawCode,
        message: rawMessage,
        fields: rawFields,
      } = detail as {
        code?: unknown;
        message?: unknown;
        fields?: unknown;
      };
      if (isErrorCode(rawCode)) {
        code = rawCode;
        message = FALLBACK_MESSAGES[code];
      }
      if (typeof rawMessage === "string" && rawMessage.length > 0) {
        message = rawMessage;
      }
      if (Array.isArray(rawFields)) {
        fields = rawFields as FieldError[];
      }
    }
  } catch {
    message = FALLBACK_MESSAGES[code];
  }
  return new ApiError(message, {
    code,
    fields,
    retryAfter: Number.isFinite(retryAfter) ? retryAfter : null,
    status: response.status,
  });
};

interface RequestOptions {
  body?: unknown;
  headers?: Record<string, string>;
  method?: "GET" | "POST" | "PATCH";
  signal?: AbortSignal;
}

const request = async <T>(
  path: string,
  { method = "GET", body, headers = {}, signal }: RequestOptions = {}
): Promise<T> => {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      body: body === undefined ? undefined : JSON.stringify(body),
      headers: {
        accept: "application/json",
        ...(body === undefined ? {} : { "content-type": "application/json" }),
        ...headers,
      },
      method,
      signal,
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(FALLBACK_MESSAGES.network, {
      cause: error,
      code: "network",
      status: 0,
    });
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  return (await response.json()) as T;
};

const query = (params: Record<string, string | number | undefined>) => {
  const entries = Object.entries(params).filter(
    (entry): entry is [string, string | number] =>
      entry[1] !== undefined && entry[1] !== ""
  );
  if (entries.length === 0) {
    return "";
  }
  return `?${entries
    .map(
      ([key, value]) =>
        `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`
    )
    .join("&")}`;
};

export const api = {
  categories: (signal?: AbortSignal) =>
    request<Category[]>("/api/categories", { signal }),
  innovation: (slug: string, signal?: AbortSignal) =>
    request<InnovationDetail>(`/api/innovations/${encodeURIComponent(slug)}`, {
      signal,
    }),
  innovations: (
    params: { category?: string; q?: string; page?: number; per_page?: number },
    signal?: AbortSignal
  ) =>
    request<Page<InnovationSummary>>(`/api/innovations${query(params)}`, {
      signal,
    }),
  match: (body: MatchRequest, signal?: AbortSignal) =>
    request<MatchResponse>("/api/match", { body, method: "POST", signal }),
  patchNeed: (id: string, token: string, body: NeedPatch) =>
    request<NeedPatchResponse>(`/api/needs/${encodeURIComponent(id)}`, {
      body,
      headers: { "x-need-token": token },
      method: "PATCH",
    }),
  powiats: (signal?: AbortSignal) =>
    request<Powiat[]>("/api/powiats", { signal }),
};

export const errorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : FALLBACK_MESSAGES.internal;
