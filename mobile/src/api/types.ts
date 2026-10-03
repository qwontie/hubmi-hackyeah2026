export interface CategoryRef {
  name: string;
  slug: string;
}

export interface Category extends CategoryRef {
  count: number;
  icon_url: string | null;
}

export interface Powiat {
  name: string;
  slug: string;
}

export interface InnovationSummary {
  category: CategoryRef;
  has_materials: boolean;
  has_video: boolean;
  lead: string;
  slug: string;
  title: string;
}

export interface InnovationDetail extends InnovationSummary {
  authors: string[];
  brochure_url: string | null;
  effectiveness: string | null;
  license: string | null;
  materials_url: string | null;
  problems: string;
  qr_url: string | null;
  source_url: string;
  target_group: string;
  terms_url: string | null;
  updated_at: string;
  video_url: string | null;
  what_it_is: string;
  who_can_use: string;
}

export interface ClusterRef {
  id: string;
  size: number;
  title: string;
}

export interface Page<T> {
  items: T[];
  page: number;
  per_page: number;
  total: number;
}

export interface MatchResult {
  innovation: InnovationSummary;
  reason: string;
  score: number;
}

export interface MatchResponse {
  cluster: ClusterRef | null;
  degraded: boolean;
  need: { id: string; edit_token: string; number?: number | null };
  results: MatchResult[];
  similar_count: number;
}

export interface MatchRequest {
  powiat?: string;
  text: string;
}

export interface NeedPatch {
  contact_consent?: boolean;
  contact_email?: string;
  nothing_fits?: boolean;
  powiat?: string;
}

export interface NeedPatchResponse {
  id: string;
  status: "new" | "answered" | "closed";
}

export type ErrorCode =
  | "bad_request"
  | "unauthorized"
  | "not_found"
  | "conflict"
  | "validation_error"
  | "text_too_short"
  | "text_too_long"
  | "unclear_text"
  | "rate_limited"
  | "ai_unavailable"
  | "internal"
  | "network";

export interface FieldError {
  field: string;
  message: string;
}
