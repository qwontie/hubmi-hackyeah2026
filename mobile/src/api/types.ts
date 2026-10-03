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

export interface Votes {
  down: number;
  up: number;
}

export interface InnovationSummary {
  category: CategoryRef;
  has_materials: boolean;
  has_video: boolean;
  image_alt?: string | null;
  image_card_url?: string | null;
  image_label?: string | null;
  image_source?: "rops" | "youtube" | "generated" | null;
  image_url?: string | null;
  lead: string;
  slug: string;
  title: string;
  votes?: Votes;
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
  need: { id: string; edit_token: string; number?: number | null } | null;
  reason?: "unclear" | "no_match" | null;
  results: MatchResult[];
  similar_count: number;
}

export interface MatchRequest {
  text: string;
}

export interface NeedCreate extends MatchRequest {
  contact_consent?: boolean;
  contact_email?: string;
  powiat?: string;
  shown_innovation_slugs?: string[];
  website?: string;
}

export interface NeedCreated {
  cluster: ClusterRef | null;
  duplicate?: boolean;
  edit_token: string;
  id: string;
  number: number;
  similar_count: number;
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
  | "call_not_open"
  | "validation_error"
  | "text_too_short"
  | "text_too_long"
  | "unclear_text"
  | "too_few_words"
  | "too_many_links"
  | "spam_rejected"
  | "report_locked"
  | "rate_limited"
  | "ai_unavailable"
  | "internal"
  | "too_many_messages"
  | "visualisation_limit"
  | "network";

export interface FieldError {
  field: string;
  message: string;
}

export interface ThreadMessage {
  author?: "rops" | "expert" | "author";
  body: string;
  direction: "to_author" | "from_author";
  expert?: { display_name: string; expertise: string | null } | null;
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

export interface LocalFact {
  label: string;
  page: number | null;
  region_value: number | null;
  source_title: string;
  source_url: string;
  unit: string;
  value: number;
  year: number;
}

export interface LocalChallenge {
  area: string;
  pages: number[];
  slug: string;
  source_title: string;
  source_url: string;
  summary: string;
  title: string;
}

export interface AdaptationPlan {
  combine: { slug: string; title: string; lead: string; why: string }[];
  cost_drivers: string[];
  local_context?: string;
  local_facts?: LocalFact[];
  measures: string[];
  partners: string[];
  regional_challenges?: LocalChallenge[];
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

export interface IdeaThread {
  can_email: boolean;
  idea: {
    id: string;
    number: number | null;
    title: string;
    status: "new" | "in_review" | "accepted" | "rejected";
    created_at: string;
  };
  messages: ThreadMessage[];
}

export interface Ref {
  name: string;
  slug: string;
}

export interface CountedRef extends Ref {
  count: number;
}

export interface Figure {
  document_title: string;
  document_url: string;
  label: string;
  page: number;
  quote: string;
  scope: "Polska" | "Małopolska" | string;
  source_title: string | null;
  unit: string | null;
  value: string;
  year: number | null;
}

export interface MaterialSummary {
  file_size: number | null;
  file_url: string;
  id: string;
  kind: Ref;
  pages: number | null;
  source_url: string;
  summary: string;
  summary_ai: boolean;
  title: string;
  topics: Ref[];
  year: number | null;
}

export interface ChallengeSummary {
  area: Ref;
  figures: Figure[];
  id: string;
  slug: string;
  source: { title: string; url: string; pages: number[] };
  summary: string;
  title: string;
  verified: boolean;
}

export interface RelatedInnovation extends InnovationSummary {
  score: number;
}

export interface MaterialDetail extends MaterialSummary {
  related_challenges: (ChallengeSummary & { score: number })[];
  related_innovations: RelatedInnovation[];
  source_section: string | null;
  updated_at: string;
}

export interface ChallengeDetail extends ChallengeSummary {
  description: string;
  related_innovations: RelatedInnovation[];
  related_materials: (MaterialSummary & { score: number })[];
  updated_at: string;
  verified_at: string | null;
}

export interface MaterialFilters {
  kinds: CountedRef[];
  topics: CountedRef[];
}

export interface PowiatFigure {
  key: string;
  label: string;
  page: number;
  source_title: string;
  source_url: string;
  unit: string | null;
  value: number;
  year: number | null;
}

export interface MapIndicator {
  key: string;
  label: string;
  max: number;
  min: number;
  page: number;
  regional: number | null;
  source_title: string;
  source_url: string;
  unit: string | null;
  year: number | null;
}

export interface MapProblem {
  answered: number;
  open: number;
  title: string;
}

export interface MapPowiat {
  figures: PowiatFigure[];
  name: string;
  needs_answered?: number;
  needs_open?: number;
  other_answered?: number;
  other_open?: number;
  problems?: MapProblem[];
  slug: string;
}

export interface MapData {
  geojson_url: string;
  indicators: MapIndicator[];
  needs_answered?: number;
  needs_open?: number;
  needs_without_powiat?: number;
  powiats: MapPowiat[];
  problem_min_needs?: number;
}

export interface PowiatFeature {
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: number[][][] | number[][][][];
  };
  id: string;
  properties: { slug: string; name: string };
  type: "Feature";
}

export interface PowiatGeo {
  features: PowiatFeature[];
  type: "FeatureCollection";
}

export interface Problem {
  category: CategoryRef | null;
  id: string;
  ideas_count: number;
  needs_answered: number;
  needs_open: number;
  needs_total: number;
  powiats: string[];
  summary: string;
  title: string;
}

export interface PublicIdea {
  canvas: Partial<Canvas> | null;
  created_at: string;
  essence: string;
  for_whom: string;
  id: string;
  number: number | null;
  powiat: string | null;
  problem_id?: string | null;
  stage: string;
  title: string;
  visualisation_alt: string | null;
  visualisation_url: string | null;
}

export interface AuthorIdea extends PublicIdea {
  has_contact: boolean;
  status: "new" | "in_review" | "accepted" | "rejected";
  updated_at: string;
  visualisations_left: number;
}

export interface IdeaVisualisation {
  alt: string;
  created_at: string;
  generations_left: number;
  generations_used: number;
  url: string;
}

export interface GrantSection {
  hint: string;
  key: string;
  label: string;
  max_length: number;
  required: boolean;
}

export interface GrantCall {
  closes_at: string;
  demo: boolean;
  description: string;
  id: string;
  opens_at: string;
  phase: "upcoming" | "open" | "closed";
  sections: GrantSection[];
  source_url: string | null;
  title: string;
  updated_at: string;
}

export interface ApplicationSection extends GrantSection {
  missing: string[];
  source: "ai" | "author";
  text: string;
}

export interface GrantApplication {
  call: Pick<
    GrantCall,
    "id" | "title" | "opens_at" | "closes_at" | "phase" | "demo"
  >;
  created_at: string;
  id: string;
  idea: { id: string; number: number; title: string };
  missing_required: string[];
  number: number;
  pdf_url: string;
  sections: ApplicationSection[];
  status: "draft" | "submitted" | "in_review" | "accepted" | "rejected";
  submitted_at: string | null;
  updated_at: string;
}

export interface Meta {
  demo: boolean;
}

export interface ProblemDetail extends Problem {
  ideas: PublicIdea[];
  innovations: InnovationSummary[];
}

export interface VoteResponse {
  id?: string;
  kind?: FeedbackKind;
  summary: FeedbackSummary;
  votes?: Votes;
}

export interface DemandRequest {
  contact_consent: boolean;
  email?: string;
  powiat: string;
  website?: string;
}

export interface DemandResult {
  count: number;
  duplicate: boolean;
}

export interface VolunteerRequest {
  contact_consent: boolean;
  email: string;
  organization?: string;
  powiat: string;
  proposal: string;
  website?: string;
  who: TesterRole;
}

export type VolunteerRecommend = "yes" | "after_changes" | "no";

export interface VolunteerReport {
  activity: string;
  not_worked: string;
  participants: number;
  recommend: VolunteerRecommend;
  worked: string;
}

export interface VolunteerView {
  editable: boolean;
  id: string;
  innovation: { slug: string; title: string };
  powiat: string;
  powiat_name: string;
  proposal: string;
  report: VolunteerReport | null;
  status: "new" | "accepted" | "rejected" | "reported" | "closed";
}

export interface ExpertNeedItem {
  created_at: string;
  id: string;
  number: number | null;
  powiat: string | null;
  text: string;
  title: string | null;
}

export interface ExpertAnswer {
  body: string;
  created_at: string;
  id: string;
}

export interface ExpertAnswerView {
  answers: ExpertAnswer[];
  expert: { display_name: string | null; expertise: string | null };
  id: string;
  item: ExpertNeedItem | PublicIdea;
  kind: "need" | "idea";
  note: string | null;
  status: "open" | "answered";
  title: string;
}
