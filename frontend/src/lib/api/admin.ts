import { api } from "$lib/api/client";

export type NeedStatus = "new" | "answered" | "closed";

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
  body: string;
  delivery_status: "pending" | "sent" | "skipped" | "failed" | null;
  direction: "to_author" | "from_author";
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
  last_need_at: string | null;
  new_last_7d: number;
  powiats?: { count: number; name: string; slug: string }[];
  size: number;
  summary: string;
  summary_stale?: boolean;
  title: string;
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
  stage: string;
  status: IdeaStatus;
  title: string;
  updated_at?: string;
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

export type SignupStatus = "new" | "contacted" | "closed";

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

export const feedbackByInnovation = (sort: string) =>
  api.get<Page<FeedbackByInnovation>>("/admin/feedback/by-innovation", {
    per_page: 100,
    sort,
  });

export const listComments = () =>
  api.get<Page<AdminFeedback>>("/admin/feedback", { per_page: 50 });

export const listSignups = () =>
  api.get<Page<AdminTestSignup>>("/admin/test-signups", { per_page: 100 });

export const setSignupStatus = (id: string, status: SignupStatus) =>
  api.patch<AdminTestSignup>(`/admin/test-signups/${id}`, { status });
