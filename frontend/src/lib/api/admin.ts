import { api, type Params } from "$lib/api/client";

export type NeedStatus = "new" | "answered" | "closed" | "junk";

export interface NeedCounts {
  answered: number;
  closed: number;
  junk: number;
  total: number;
  unread: number;
  waiting: number;
}

export interface Page<T> {
  items: T[];
  page: number;
  per_page: number;
  total: number;
}

export interface ClusterRef {
  id: string;
  size: number;
  title: string;
}

export interface NeedMatchRef {
  score: number;
  slug: string;
  title: string;
}

export interface AdminNeed {
  category_slug: string | null;
  cluster: ClusterRef | null;
  contact_email?: string | null;
  created_at: string;
  has_contact?: boolean;
  id: string;
  last_message_at?: string | null;
  matches: NeedMatchRef[];
  messages_count?: number;
  nothing_fits: boolean;
  number?: number | null;
  origin: "match" | "form";
  powiat: string | null;
  status: NeedStatus;
  text: string;
  title?: string | null;
  unread?: number;
  updated_at?: string;
}

export interface NeedMatch {
  innovation: {
    category: { name: string; slug: string };
    lead?: string;
    slug: string;
    title: string;
  };
  rank: number;
  reason: string;
  score: number;
}

export interface Message {
  admin: { id: string; login: string } | null;
  application_id?: string | null;
  body: string;
  delivery_status: "pending" | "sent" | "skipped" | "failed" | null;
  direction: "to_author" | "from_author";
  expert?: { display_name: string; expertise: string | null } | null;
  id: string;
  idea_id?: string | null;
  need_id: string | null;
  read_at?: string | null;
  sent_at: string;
}

export interface AdminNeedDetail extends AdminNeed {
  can_email: boolean;
  match_details: NeedMatch[];
  messages: Message[];
}

export interface AdminCluster {
  category_name?: string | null;
  category_slug: string | null;
  created_at: string;
  daily?: number[];
  id: string;
  ideas_count?: number;
  last_need_at: string | null;
  new_last_7d: number;
  powiats?: { count: number; name: string; slug: string }[];
  size: number;
  summary: string;
  summary_stale?: boolean;
  title: string;
  title_locked?: boolean;
  waiting?: number;
}

export interface Powiat {
  name: string;
  slug: string;
}

export const listNeeds = (
  params: {
    cluster_id?: string;
    page?: number;
    per_page?: number;
    status?: NeedStatus;
  },
  signal?: AbortSignal
) =>
  api.get<Page<AdminNeed>>(
    "/admin/needs",
    { per_page: 100, ...params },
    signal
  );

export const needCounts = (signal?: AbortSignal) =>
  api.get<NeedCounts>("/admin/needs/counts", undefined, signal);

export const getNeed = (id: string, signal?: AbortSignal) =>
  api.get<AdminNeedDetail>(`/admin/needs/${id}`, undefined, signal);

export const setNeedStatus = (id: string, status: NeedStatus) =>
  api.patch<AdminNeed>(`/admin/needs/${id}`, { status });

export const markNeedRead = (id: string) =>
  api.post<void>(`/admin/needs/${id}/read`);

export const replyToNeed = (id: string, body: string) =>
  api.post<Message>(`/admin/needs/${id}/reply`, { body });

export const listClusters = (signal?: AbortSignal) =>
  api.get<Page<AdminCluster>>(
    "/admin/clusters",
    { per_page: 100, sort: "size" },
    signal
  );

export const listPowiats = () => api.get<Powiat[]>("/powiats");

export const mergeCluster = (id: string, intoId: string) =>
  api.post<AdminCluster>(`/admin/clusters/${id}/merge`, { into_id: intoId });

export const splitCluster = (id: string, needIds: string[]) =>
  api.post<{ created: AdminCluster; source: AdminCluster }>(
    `/admin/clusters/${id}/split`,
    { need_ids: needIds }
  );

export const refreshCluster = (id: string) =>
  api.post<AdminCluster>(`/admin/clusters/${id}/refresh`);

export const renameCluster = (id: string, title: string) =>
  api.patch<AdminCluster>(`/admin/clusters/${id}`, { title });

export interface Category {
  count: number;
  icon_url: string | null;
  name: string;
  slug: string;
}

export interface AdminInnovation {
  category: { name: string; slug: string };
  edited_at: string | null;
  edited_fields: string[];
  has_materials: boolean;
  has_video: boolean;
  imported_at: string | null;
  lead: string | null;
  slug: string;
  source_url: string | null;
  status: "draft" | "published";
  title: string;
  updated_at: string;
}

export interface AdminInnovationDetail extends AdminInnovation {
  authors: string[];
  brochure_url: string | null;
  created_at: string;
  effectiveness: string | null;
  license: string | null;
  materials_url: string | null;
  problems: string | null;
  qr_url: string | null;
  target_group: string | null;
  video_url: string | null;
  what_it_is: string | null;
  who_can_use: string | null;
}

export interface ImportRun {
  created: number;
  error: string | null;
  failed: number;
  finished_at: string | null;
  id: string;
  skipped_edited: number;
  started_at: string;
  status: "running" | "done" | "failed";
  total: number;
  trigger: "script" | "admin";
  unchanged: number;
  updated: number;
}

export interface ImportProgress {
  created: number;
  current: string | null;
  done: number;
  failed: number;
  run_id: string;
  skipped_edited: number;
  total: number;
  unchanged: number;
  updated: number;
}

export const listCategories = () => api.get<Category[]>("/categories");

export async function listAllInnovations(): Promise<AdminInnovation[]> {
  const first = await api.get<Page<AdminInnovation>>("/admin/innovations", {
    page: 1,
    per_page: 100,
    sort: "title",
  });
  const pages = Math.ceil(first.total / 100);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, pages - 1) }, (_, n) =>
      api.get<Page<AdminInnovation>>("/admin/innovations", {
        page: n + 2,
        per_page: 100,
        sort: "title",
      })
    )
  );
  return [first, ...rest].flatMap((p) => p.items);
}

export const getInnovation = (slug: string, signal?: AbortSignal) =>
  api.get<AdminInnovationDetail>(
    `/admin/innovations/${slug}`,
    undefined,
    signal
  );

export const patchInnovation = (
  slug: string,
  body: Partial<AdminInnovationDetail>
) => api.patch<AdminInnovationDetail>(`/admin/innovations/${slug}`, body);

export const publishInnovation = (slug: string, publish: boolean) =>
  api.post<AdminInnovationDetail>(
    `/admin/innovations/${slug}/${publish ? "publish" : "unpublish"}`
  );

export const runImport = () =>
  api.post<{ run_id: string }>("/admin/import/run");

export const listImportRuns = () =>
  api.get<ImportRun[]>("/admin/import/runs", { limit: 5 });

export type IdeaStatus = "new" | "in_review" | "accepted" | "rejected";

export interface AdminIdea {
  canvas: Record<string, string> | null;
  contact_email: string | null;
  created_at: string;
  essence: string;
  for_whom: string;
  has_contact?: boolean;
  id: string;
  number: number;
  powiat: string | null;
  problem?: { id: string; title: string } | null;
  problem_id?: string | null;
  stage: string;
  status: IdeaStatus;
  title: string;
  updated_at?: string;
  visualisation_alt?: string | null;
  visualisation_url?: string | null;
}

export interface AdminIdeaDetail extends AdminIdea {
  similar_ideas: {
    essence: string;
    id: string;
    number: number;
    similarity: number;
    stage: string;
    title: string;
  }[];
  similar_innovations: {
    lead: string | null;
    similarity: number;
    slug: string;
    title: string;
  }[];
  visualisation_prompt?: string | null;
}

export interface IdeaOptions {
  canvas_fields: { field: string; name: string }[];
  stages: { name: string; slug: string }[];
}

export const listIdeas = () =>
  api.get<Page<AdminIdea>>("/admin/ideas", { per_page: 100 });

export const getIdea = (id: string, signal?: AbortSignal) =>
  api.get<AdminIdeaDetail>(`/admin/ideas/${id}`, undefined, signal);

export const setIdeaStatus = (id: string, status: IdeaStatus) =>
  api.patch<AdminIdeaDetail>(`/admin/ideas/${id}`, { status });

export const ideaOptions = () => api.get<IdeaOptions>("/ideas/options");

export const listIdeaMessages = (id: string) =>
  api.get<Message[]>(`/admin/ideas/${id}/messages`);

export const replyToIdea = (id: string, body: string) =>
  api.post<Message>(`/admin/ideas/${id}/reply`, { body });

export const markIdeaRead = (id: string) =>
  api.post<void>(`/admin/ideas/${id}/read`);

async function allPages<T>(path: string, params: Params = {}): Promise<T[]> {
  const first = await api.get<Page<T>>(path, {
    ...params,
    page: 1,
    per_page: 100,
  });
  const pages = Math.ceil(first.total / 100);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, pages - 1) }, (_, n) =>
      api.get<Page<T>>(path, { ...params, page: n + 2, per_page: 100 })
    )
  );
  return [first, ...rest].flatMap((p) => p.items);
}

export interface FeedbackByInnovation {
  does_not_fit: number;
  fits: number;
  improvements: number;
  innovation: { slug: string; title: string };
  last_at: string | null;
  testers: number;
}

export interface AdminFeedback {
  comment: string | null;
  created_at: string;
  id: string;
  innovation: { slug: string; title: string };
  kind: "fits" | "does_not_fit" | "improvement";
  need_id: string | null;
  updated_at: string;
}

export type SignupStatus = VolunteerStatus;

export interface AdminTestSignup {
  contact_email: string;
  created_at: string;
  id: string;
  innovation: { slug: string; title: string };
  note: string | null;
  organization: string | null;
  powiat: string | null;
  status: SignupStatus;
  who: "resident" | "ngo" | "local_government" | "expert";
}

export const feedbackByInnovation = () =>
  allPages<FeedbackByInnovation>("/admin/feedback/by-innovation", {
    sort: "recent",
  });

export const listFeedback = () => allPages<AdminFeedback>("/admin/feedback");

export const listSignups = () =>
  allPages<AdminTestSignup>("/admin/test-signups");

export const listAllNeeds = () => allPages<AdminNeed>("/admin/needs");

export interface Ref {
  name: string;
  slug: string;
}

export interface Figure {
  document_title: string;
  document_url: string;
  label: string;
  page: number;
  quote: string;
  scope: string;
  source_title: string;
  unit: string | null;
  value: string;
  year: number | null;
}

export interface AdminChallenge {
  area: Ref;
  description: string;
  edited_fields: string[];
  figures: Figure[];
  id: string;
  position: number;
  slug: string;
  source: { pages: number[]; title: string; url: string };
  status: "draft" | "published";
  summary: string;
  title: string;
  verified: boolean;
  verified_at: string | null;
  verified_by: string | null;
}

export interface AdminMaterial {
  edited_fields: string[];
  file_size: number | null;
  file_url: string;
  id: string;
  kind: Ref;
  pages: number | null;
  source_url: string | null;
  status: "draft" | "published";
  summary: string;
  summary_ai: boolean;
  summary_state: string;
  title: string;
  topics: Ref[];
  year: number | null;
}

export interface KnowledgeRun {
  counters: Record<string, unknown>;
  done: number;
  error: string | null;
  finished_at: string | null;
  id: string;
  started_at: string;
  status: "running" | "done" | "failed";
  step: string | null;
  total: number;
}

export const listChallenges = () =>
  allPages<AdminChallenge>("/admin/challenges");
export const listMaterials = () => allPages<AdminMaterial>("/admin/materials");
export const challengeAreas = () =>
  api.get<(Ref & { count: number })[]>("/challenges/areas");
export const patchChallenge = (id: string, body: Record<string, unknown>) =>
  api.patch<AdminChallenge>(`/admin/challenges/${id}`, body);
export const patchMaterial = (id: string, body: Record<string, unknown>) =>
  api.patch<AdminMaterial>(`/admin/materials/${id}`, body);
export const runKnowledgeImport = () =>
  api.post<{ run_id: string }>("/admin/knowledge/import/run");
export const knowledgeRuns = () =>
  api.get<KnowledgeRun[]>("/admin/knowledge/import/runs", { limit: 3 });

export interface Expert {
  answered: number;
  display_name: string;
  expertise: string | null;
  has_email: boolean;
  id: string;
  login: string;
  open: number;
}

export interface Assignment {
  answered_at: string | null;
  assigned_by: string;
  created_at: string;
  delivery_status?: "pending" | "sent" | "skipped" | "failed" | null;
  expert: {
    display_name: string;
    email?: string | null;
    expertise: string | null;
    id: string | null;
  };
  id: string;
  idea_id: string | null;
  kind: "need" | "idea";
  need_id: string | null;
  note: string | null;
  opinions_count: number;
  private_notes?: { body: string; created_at: string; id: string }[];
  status: "open" | "answered";
  title: string;
}

export interface ExpertAssignmentDetail extends Assignment {
  item: {
    canvas?: Record<string, string> | null;
    created_at: string;
    essence?: string;
    for_whom?: string;
    id: string;
    number: number | null;
    powiat: string | null;
    stage?: string;
    status: string;
    text?: string;
    title: string | null;
    visualisation_alt?: string | null;
    visualisation_url?: string | null;
  };
  messages: Message[];
}

export const listExperts = () => api.get<Expert[]>("/admin/experts");

export const listAssignments = (kind: "needs" | "ideas", id: string) =>
  api.get<Assignment[]>(`/admin/${kind}/${id}/assignments`);

export const assignExpert = (
  kind: "needs" | "ideas",
  id: string,
  expertId: string,
  note: string
) =>
  api.post<Assignment>(`/admin/${kind}/${id}/assign`, {
    expert_id: expertId,
    note: note || undefined,
  });

export const unassign = (id: string) => api.del(`/admin/assignments/${id}`);

export const forwardToExpert = (
  kind: "needs" | "ideas",
  id: string,
  body: {
    email: string;
    expertise?: string | null;
    name?: string | null;
    note?: string | null;
  }
) => api.post<Assignment>(`/admin/${kind}/${id}/forward`, body);

export const resendToExpert = (id: string) =>
  api.post<Assignment>(`/admin/assignments/${id}/resend`, {});

export interface ExpertContact {
  assignments: number;
  email: string;
  expertise: string | null;
  last_at: string | null;
  name: string | null;
}

export const expertContacts = () =>
  api.get<ExpertContact[]>("/admin/experts/contacts");

export const applicationMessages = (id: string) =>
  api.get<Message[]>(`/admin/applications/${id}/messages`);

export const replyToApplication = (id: string, body: string) =>
  api.post<Message>(`/admin/applications/${id}/reply`, { body });

export const myAssignments = () => api.get<Assignment[]>("/expert/assignments");

export const myAssignment = (id: string, signal?: AbortSignal) =>
  api.get<ExpertAssignmentDetail>(
    `/expert/assignments/${id}`,
    undefined,
    signal
  );

export const sendOpinion = (id: string, body: string, privateNote: string) =>
  api.post<{
    assignment: Assignment;
    message: Message | null;
    private_note: { body: string; created_at: string; id: string } | null;
  }>(`/expert/assignments/${id}/opinion`, {
    body: body || undefined,
    private_note: privateNote || undefined,
  });

export interface ReplyFragment {
  id: string;
  innovation: { slug: string; title: string; url: string } | null;
  kind: "opening" | "innovation" | "next_step" | "closing";
  label: string;
  text: string;
}

export interface EarlierAnswer {
  body: string;
  demo: boolean;
  need_excerpt: string;
  need_number: number | null;
  sent_at: string;
  similarity: number;
}

export interface ReplySuggestions {
  earlier_answers: EarlierAnswer[];
  fragments: ReplyFragment[];
  generated_at: string;
}

export const storedReplySuggestions = (id: string, signal?: AbortSignal) =>
  api.get<ReplySuggestions | undefined>(
    `/admin/needs/${id}/reply-suggestions`,
    undefined,
    signal
  );

export const replySuggestions = (
  id: string,
  refresh: boolean,
  signal?: AbortSignal
) =>
  api.post<ReplySuggestions>(
    `/admin/needs/${id}/reply-suggestions${refresh ? "?refresh=true" : ""}`,
    undefined,
    signal
  );

export interface GrantSection {
  hint: string;
  key: string;
  label: string;
  max_length: number;
  required: boolean;
}

export type CallPhase = "upcoming" | "open" | "closed";
export type CallStatus = "draft" | "published" | "cancelled";
export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "in_review"
  | "accepted"
  | "rejected";

export interface AdminGrantCall {
  applications: {
    accepted: number;
    in_review: number;
    rejected: number;
    submitted: number;
    total: number;
  };
  closes_at: string;
  created_at: string;
  demo: boolean;
  description: string;
  id: string;
  opens_at: string;
  phase: CallPhase;
  sections: GrantSection[];
  source_url: string | null;
  status: CallStatus;
  template: string | null;
  title: string;
  updated_at: string;
}

export interface GrantTemplate {
  description: string;
  sections: GrantSection[];
  slug: string;
  source_url: string;
  title: string;
}

export interface ApplicationSummary {
  call_id: string;
  id: string;
  idea: { id: string; number: number; title: string } | null;
  missing_required: string[];
  number: number;
  status: ApplicationStatus;
  submitted_at: string | null;
  updated_at: string;
}

export interface AdminApplication {
  call: {
    closes_at: string;
    demo: boolean;
    id: string;
    opens_at: string;
    phase: CallPhase;
    title: string;
  };
  contact_consent: boolean;
  contact_email: string | null;
  created_at: string;
  id: string;
  idea: { id: string; number: number; title: string } | null;
  idea_contact: boolean;
  missing_required: string[];
  number: number;
  pdf_url: string;
  sections: (GrantSection & {
    missing: string[];
    source: "ai" | "author";
    text: string;
  })[];
  status: ApplicationStatus;
  submitted_at: string | null;
  updated_at: string;
}

export type CallBody = Partial<{
  closes_at: string;
  description: string;
  opens_at: string;
  sections: GrantSection[];
  source_url: string | null;
  status: CallStatus;
  template: string;
  title: string;
}>;

export const listGrantCalls = () =>
  allPages<AdminGrantCall>("/admin/grant-calls");

export const grantTemplates = () =>
  api.get<GrantTemplate[]>("/admin/grant-templates");

export const createGrantCall = (body: CallBody) =>
  api.post<AdminGrantCall>("/admin/grant-calls", body);

export const patchGrantCall = (id: string, body: CallBody) =>
  api.patch<AdminGrantCall>(`/admin/grant-calls/${id}`, body);

export const deleteGrantCall = (id: string) =>
  api.del(`/admin/grant-calls/${id}`);

export const callApplications = (id: string) =>
  allPages<ApplicationSummary>(`/admin/grant-calls/${id}/applications`);

export const getApplication = (id: string, signal?: AbortSignal) =>
  api.get<AdminApplication>(`/admin/applications/${id}`, undefined, signal);

export const setApplicationStatus = (
  id: string,
  status: "in_review" | "accepted" | "rejected"
) => api.patch<AdminApplication>(`/admin/applications/${id}`, { status });

export type IngestResult =
  | { id: string; kind: "material"; title: string }
  | { kind: "innovation"; slug: string; title: string };

export interface IngestJob {
  done?: number;
  error?: string | null;
  existing?: IngestResult | null;
  job_id: string;
  result?: IngestResult | null;
  status: "running" | "done" | "failed";
  step?: "fetch" | "text" | "summary" | "save" | "embedding";
  total?: number;
}

export const addMaterial = (
  body:
    | { kind: "url"; url: string; title?: string }
    | { kind: "text"; text: string; title: string }
) => api.post<{ job_id: string }>("/admin/materials", body);

export const uploadMaterial = (file: File, title?: string) => {
  const form = new FormData();
  form.set("file", file);
  if (title) {
    form.set("title", title);
  }
  return api.postForm<{ job_id: string }>("/admin/materials/upload", form);
};

export const ingestJob = (id: string) =>
  api.get<IngestJob>(`/admin/materials/jobs/${id}`);

export interface ContactProfile {
  email: string;
  feedback: {
    created_at: string;
    id: string;
    innovation: { slug: string; title: string };
    kind: AdminFeedback["kind"];
    need_id: string;
  }[];
  ideas: {
    created_at: string;
    id: string;
    number: number;
    powiat: string | null;
    status: IdeaStatus;
    title: string;
  }[];
  needs: {
    created_at: string;
    id: string;
    number: number | null;
    powiat: string | null;
    status: NeedStatus;
    text: string;
    title: string | null;
  }[];
  test_signups: AdminTestSignup[];
}

export const contactProfile = (email: string) =>
  api.post<ContactProfile>("/admin/contact-profile", { email });

export interface GrantSubscriber {
  confirmed_at: string | null;
  consent_at: string;
  created_at: string;
  email: string;
  failed: number;
  id: string;
  sent: number;
  state: "pending" | "confirmed" | "unsubscribed";
  unsubscribed_at: string | null;
}

export interface GrantSubscriberList {
  items: GrantSubscriber[];
  totals: {
    confirmed: number;
    failed_deliveries: number;
    pending: number;
    unsubscribed: number;
  };
}

export const grantSubscribers = (signal?: AbortSignal) =>
  api.get<GrantSubscriberList>("/admin/grant-subscribers", undefined, signal);

export const removeGrantSubscriber = (id: string) =>
  api.del(`/admin/grant-subscribers/${id}`);

export interface AdminAdaptation {
  context: string;
  created_at: string;
  id: string;
  innovation: { slug: string; title: string };
  institution: { name: string; slug: string };
  place: string;
  powiat: string | null;
  service_name: string;
  share_path: string;
}

export interface AdaptationPlan {
  combine: { lead: string | null; slug: string; title: string; why: string }[];
  cost_drivers: string[];
  local_context?: string | null;
  local_facts?: {
    label: string;
    page?: number | null;
    region_value?: number | null;
    source_title?: string | null;
    source_url?: string | null;
    unit?: string | null;
    value: number | string;
    year?: number | null;
  }[];
  measures: string[];
  partners: string[];
  regional_challenges?: {
    area?: string;
    slug: string;
    summary?: string;
    title: string;
  }[];
  risks: { mitigation: string; risk: string }[];
  service_name: string;
  staff: string[];
  steps: { description: string; title: string }[];
  summary: string;
  target_group: string;
  to_check: string[];
}

export interface Adaptation {
  context: string;
  created_at: string;
  id: string;
  innovation: { slug: string; title: string };
  institution: { name: string; slug: string };
  place: string;
  plan: AdaptationPlan;
  powiat: string | null;
  share_path: string;
}

export const listAdaptations = (
  params: { innovation?: string; institution_type?: string; powiat?: string },
  signal?: AbortSignal
) =>
  api.get<Page<AdminAdaptation>>(
    "/admin/adaptations",
    { per_page: 100, ...params },
    signal
  );

export const getAdaptation = (id: string, signal?: AbortSignal) =>
  api.get<Adaptation>(`/adaptations/${id}`, undefined, signal);

export type VolunteerStatus =
  | "new"
  | "accepted"
  | "rejected"
  | "reported"
  | "closed";

export interface VolunteerReport {
  activity: string;
  created_at: string;
  not_worked: string;
  participants: number;
  recommend: "yes" | "after_changes" | "no";
  updated_at: string;
  worked: string;
}

export interface AdminVolunteer {
  created_at: string;
  decided_at: string | null;
  decision_reason: string | null;
  email: string;
  id: string;
  innovation: { slug: string; title: string };
  organization: string | null;
  powiat: string;
  powiat_name: string;
  proposal: string;
  report: VolunteerReport | null;
  status: VolunteerStatus;
  updated_at: string;
  who: AdminTestSignup["who"];
}

export interface VolunteerMessage {
  admin: string | null;
  body: string;
  created_at: string;
  delivery_error: string | null;
  delivery_status: "pending" | "sent" | "skipped" | "failed";
  id: string;
  kind: "message" | "accept" | "reject";
}

export interface AdminVolunteerDetail extends AdminVolunteer {
  drafts: { accept: string; reject: string };
  messages: VolunteerMessage[];
}

export type VolunteerCounts = Record<VolunteerStatus, number>;

export const listVolunteers = (params: { innovation?: string } = {}) =>
  allPages<AdminVolunteer>("/admin/volunteers", params);

export const volunteerCounts = () =>
  api.get<VolunteerCounts>("/admin/volunteers/counts");

export const getVolunteer = (id: string, signal?: AbortSignal) =>
  api.get<AdminVolunteerDetail>(`/admin/volunteers/${id}`, undefined, signal);

export const writeToVolunteer = (id: string, body: string) =>
  api.post<VolunteerMessage>(`/admin/volunteers/${id}/messages`, { body });

export const acceptVolunteer = (id: string, body: string | null) =>
  api.post<AdminVolunteerDetail>(`/admin/volunteers/${id}/accept`, { body });

export const rejectVolunteer = (
  id: string,
  reason: string,
  body: string | null
) =>
  api.post<AdminVolunteerDetail>(`/admin/volunteers/${id}/reject`, {
    body,
    reason,
  });

export const closeVolunteer = (id: string) =>
  api.post<AdminVolunteerDetail>(`/admin/volunteers/${id}/close`, {});

export interface VolunteerReports {
  innovation: { slug: string; title: string };
  items: AdminVolunteer[];
  participants: number;
  recommend: { after_changes: number; no: number; yes: number };
  reports: number;
}

export const volunteerReports = (innovation: string, signal?: AbortSignal) =>
  api.get<VolunteerReports>(
    "/admin/volunteers/reports",
    { innovation },
    signal
  );

export interface AdaptationVolunteers {
  count: number;
  innovation: { slug: string; title: string };
  items: AdminVolunteer[];
  powiat: string | null;
  powiat_name: string | null;
}

export const adaptationVolunteers = (
  adaptationId: string,
  signal?: AbortSignal
) =>
  api.get<AdaptationVolunteers>(
    `/admin/volunteers/for-adaptation/${adaptationId}`,
    undefined,
    signal
  );

export interface DemandRow {
  count: number;
  innovation: { slug: string; title: string };
  last_at: string | null;
  powiat: string;
  powiat_name: string;
  with_email: number;
}

export const listDemand = (
  params: { innovation?: string; powiat?: string } = {},
  signal?: AbortSignal
) =>
  api.get<Page<DemandRow>>(
    "/admin/demand",
    { per_page: 100, ...params },
    signal
  );
