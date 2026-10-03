import { API_BASE } from "@/config";
import type {
  Adaptation,
  AdaptationRequest,
  AssistAnswer,
  AssistOut,
  Category,
  ChallengeDetail,
  ChallengeSummary,
  CountedRef,
  ErrorCode,
  FeedbackKind,
  FeedbackSummary,
  FieldError,
  IdeaCreate,
  IdeaCreated,
  IdeaDraft,
  IdeaOptions,
  IdeaThread,
  InnovationDetail,
  InnovationSummary,
  InstitutionType,
  MapData,
  MatchRequest,
  MatchResponse,
  MaterialDetail,
  MaterialFilters,
  MaterialSummary,
  NeedCreate,
  NeedCreated,
  NeedPatch,
  NeedPatchResponse,
  NeedThread,
  Page,
  Powiat,
  PowiatGeo,
  Problem,
  ProblemDetail,
  TestSignup,
  ThreadMessage,
  VoteResponse,
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
  text_too_short: "Opisz problem w co najmniej 5 znakach.",
  too_many_messages:
    "Wysłano już kilka wiadomości bez odpowiedzi. Poczekaj, aż ROPS odpisze.",
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
  method?: "GET" | "POST" | "PATCH" | "DELETE";
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
  adapt: (slug: string, body: AdaptationRequest, signal?: AbortSignal) =>
    request<Adaptation>(`/api/innovations/${encodeURIComponent(slug)}/adapt`, {
      body,
      method: "POST",
      signal,
    }),
  adaptation: (id: string, signal?: AbortSignal) =>
    request<Adaptation>(`/api/adaptations/${encodeURIComponent(id)}`, {
      signal,
    }),
  assist: (draft: IdeaDraft, answers: AssistAnswer[], signal?: AbortSignal) =>
    request<AssistOut>("/api/ideas/assist", {
      body: { ...draft, answers },
      method: "POST",
      signal,
    }),
  categories: (signal?: AbortSignal) =>
    request<Category[]>("/api/categories", { signal }),
  challenge: (key: string, signal?: AbortSignal) =>
    request<ChallengeDetail>(`/api/challenges/${encodeURIComponent(key)}`, {
      signal,
    }),
  challengeAreas: (signal?: AbortSignal) =>
    request<CountedRef[]>("/api/challenges/areas", { signal }),
  challenges: (
    params: { area?: string; q?: string; page?: number; per_page?: number },
    signal?: AbortSignal
  ) =>
    request<Page<ChallengeSummary>>(`/api/challenges${query(params)}`, {
      signal,
    }),
  createIdea: (body: IdeaCreate) =>
    request<IdeaCreated>("/api/ideas", { body, method: "POST" }),
  createNeed: (body: NeedCreate) =>
    request<NeedCreated>("/api/needs", { body, method: "POST" }),
  feedbackSummary: (slug: string, signal?: AbortSignal) =>
    request<FeedbackSummary>(
      `/api/innovations/${encodeURIComponent(slug)}/feedback`,
      { signal }
    ),
  ideaOptions: (signal?: AbortSignal) =>
    request<IdeaOptions>("/api/ideas/options", { signal }),
  ideaThread: (id: string, token: string, signal?: AbortSignal) =>
    request<IdeaThread>(`/api/ideas/${encodeURIComponent(id)}/thread`, {
      headers: { "x-idea-token": token },
      signal,
    }),
  improve: (slug: string, text: string) =>
    request<{ id: string }>(
      `/api/innovations/${encodeURIComponent(slug)}/improvements`,
      { body: { text }, method: "POST" }
    ),
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
  institutionTypes: (signal?: AbortSignal) =>
    request<InstitutionType[]>("/api/institution-types", { signal }),
  map: (signal?: AbortSignal) => request<MapData>("/api/map", { signal }),
  mapGeo: (url: string, signal?: AbortSignal) =>
    request<PowiatGeo>(url, { signal }),
  match: (body: MatchRequest, signal?: AbortSignal) =>
    request<MatchResponse>("/api/match", { body, method: "POST", signal }),
  material: (id: string, signal?: AbortSignal) =>
    request<MaterialDetail>(`/api/materials/${encodeURIComponent(id)}`, {
      signal,
    }),
  materialFilters: (signal?: AbortSignal) =>
    request<MaterialFilters>("/api/materials/topics", { signal }),
  materials: (
    params: {
      kind?: string;
      topic?: string;
      q?: string;
      page?: number;
      per_page?: number;
    },
    signal?: AbortSignal
  ) =>
    request<Page<MaterialSummary>>(`/api/materials${query(params)}`, {
      signal,
    }),
  patchNeed: (id: string, token: string, body: NeedPatch) =>
    request<NeedPatchResponse>(`/api/needs/${encodeURIComponent(id)}`, {
      body,
      headers: { "x-need-token": token },
      method: "PATCH",
    }),
  powiats: (signal?: AbortSignal) =>
    request<Powiat[]>("/api/powiats", { signal }),
  problem: (id: string, signal?: AbortSignal) =>
    request<ProblemDetail>(`/api/problems/${encodeURIComponent(id)}`, {
      signal,
    }),
  problems: (
    params: {
      q?: string;
      category?: string;
      powiat?: string;
      page?: number;
      per_page?: number;
    },
    signal?: AbortSignal
  ) => request<Page<Problem>>(`/api/problems${query(params)}`, { signal }),
  sendIdeaMessage: (id: string, token: string, body: string) =>
    request<ThreadMessage>(`/api/ideas/${encodeURIComponent(id)}/messages`, {
      body: { body },
      headers: { "x-idea-token": token },
      method: "POST",
    }),
  sendMessage: (id: string, token: string, body: string) =>
    request<ThreadMessage>(`/api/needs/${encodeURIComponent(id)}/messages`, {
      body: { body },
      headers: { "x-need-token": token },
      method: "POST",
    }),
  testSignup: (slug: string, body: TestSignup) =>
    request<{ id: string }>(
      `/api/innovations/${encodeURIComponent(slug)}/test-signup`,
      { body, method: "POST" }
    ),
  thread: (id: string, token: string, signal?: AbortSignal) =>
    request<NeedThread>(`/api/needs/${encodeURIComponent(id)}/thread`, {
      headers: { "x-need-token": token },
      signal,
    }),
  unvote: (slug: string, voter: string) =>
    request<VoteResponse>(
      `/api/innovations/${encodeURIComponent(slug)}/feedback`,
      { headers: { "x-voter-id": voter }, method: "DELETE" }
    ),
  vote: (
    slug: string,
    kind: FeedbackKind,
    options: { need?: { id: string; token: string }; voter?: string } = {}
  ) =>
    request<VoteResponse>(
      `/api/innovations/${encodeURIComponent(slug)}/feedback`,
      {
        body: options.need ? { kind, need_id: options.need.id } : { kind },
        headers: {
          ...(options.need ? { "x-need-token": options.need.token } : {}),
          ...(options.voter ? { "x-voter-id": options.voter } : {}),
        },
        method: "POST",
      }
    ),
};

export const errorMessage = (error: unknown) =>
  error instanceof ApiError ? error.message : FALLBACK_MESSAGES.internal;
