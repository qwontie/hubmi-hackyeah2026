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
  need_id: string;
  read_at?: string | null;
  sent_at: string;
}

export interface AdminNeedDetail extends AdminNeed {
  can_email: boolean;
  match_details: NeedMatch[];
  messages: Message[];
}

export interface AdminCluster {
  category_slug: string | null;
  created_at: string;
  daily?: number[];
  id: string;
  last_need_at: string | null;
  new_last_7d: number;
  powiats?: { count: number; name: string; slug: string }[];
  size: number;
  summary: string;
  title: string;
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
