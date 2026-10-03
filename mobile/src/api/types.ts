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
  | "too_many_messages"
  | "network";

export interface FieldError {
  field: string;
  message: string;
}

export interface ThreadMessage {
  body: string;
  direction: "to_author" | "from_author";
  id: string;
  sent_at: string;
}

export interface NeedThread {
  can_email: boolean;
  messages: ThreadMessage[];
  need: {
    id: string;
    number: number | null;
    text: string;
    status: "new" | "answered" | "closed";
    created_at: string;
  };
}

export interface FeedbackSummary {
  does_not_fit: number;
  fits: number;
  improvements: number;
  testers: number;
}

export type FeedbackKind = "fits" | "does_not_fit";

export type TesterRole = "resident" | "ngo" | "local_government" | "expert";

export interface TestSignup {
  contact_consent: true;
  contact_email: string;
  note?: string;
  organization?: string;
  powiat?: string;
  who: TesterRole;
}

export interface InstitutionType {
  name: string;
  slug: string;
}

export interface AdaptationRequest {
  context: string;
  institution_type: string;
  place: string;
  powiat?: string;
}

export interface AdaptationPlan {
  combine: { slug: string; title: string; lead: string; why: string }[];
  cost_drivers: string[];
  measures: string[];
  partners: string[];
  risks: { risk: string; mitigation: string }[];
  service_name: string;
  staff: string[];
  steps: { title: string; description: string }[];
  summary: string;
  target_group: string;
  to_check: string[];
}

export interface Adaptation {
  context: string;
  created_at: string;
  id: string;
  innovation: { slug: string; title: string };
  institution: InstitutionType;
  place: string;
  plan: AdaptationPlan;
  powiat: string | null;
  share_path: string;
}

export type CanvasField =
  | "problem"
  | "users"
  | "solution"
  | "novelty"
  | "resources"
  | "partners"
  | "micro_test"
  | "measures";

export type Canvas = Record<CanvasField, string | null>;

export interface IdeaOptions {
  canvas_fields: { field: CanvasField; name: string }[];
  stages: { slug: string; name: string }[];
}

export interface IdeaDraft {
  canvas?: Partial<Canvas>;
  essence?: string;
  for_whom?: string;
  stage?: string;
  title?: string;
}

export interface AssistAnswer {
  answer: string;
  question: string;
}

export interface AssistOut {
  canvas: Canvas;
  inspirations: { slug: string; title: string; lead: string; why: string }[];
  missing: CanvasField[];
  questions: { field: CanvasField; question: string }[];
  suggestions: string[];
}

export interface IdeaCreate {
  canvas?: Partial<Canvas>;
  contact_consent?: boolean;
  contact_email?: string;
  essence: string;
  for_whom: string;
  powiat?: string;
  stage: string;
  title: string;
}

export interface IdeaCreated {
  edit_token: string;
  id: string;
  number: number;
  similar_ideas: {
    id: string;
    number: number;
    title: string;
    essence: string;
    stage: string;
    similarity: number;
  }[];
  similar_innovations: {
    slug: string;
    title: string;
    lead: string;
    similarity: number;
  }[];
}
