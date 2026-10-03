import type { AdminCluster } from "$lib/api/admin";

export interface FolderTab {
  cluster: AdminCluster | null;
  fresh: number;
  href: string;
  id: string;
  size: number;
  title: string;
  week: number;
}

export interface MenuItem {
  hint?: string;
  label: string;
  run: () => void;
  tone?: "bad";
}
