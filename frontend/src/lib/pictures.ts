import type { AdminInnovationDetail, Page } from "$lib/api/admin";
import { api } from "$lib/api/client";

export interface PictureFields {
  image_alt?: string | null;
  image_card_url?: string | null;
  image_label?: string | null;
  image_source?: string | null;
  image_url?: string | null;
  volunteer_checked?: boolean;
  volunteer_reports?: number;
}

export const hasPicture = (item: PictureFields) =>
  Boolean(item.image_url && item.image_card_url);

export const onBroken = (fail: () => void) => (node: HTMLImageElement) => {
  if (node.complete && node.naturalWidth === 0 && node.src) {
    fail();
  }
  node.addEventListener("error", fail);
  return () => node.removeEventListener("error", fail);
};

export interface PoolPicture extends PictureFields {
  category: { name: string; slug: string };
  id: string;
  title: string;
}

export const listPicturePool = () =>
  api.get<PoolPicture[]>("/admin/innovations/picture-pool");

export const usePoolPicture = (slug: string, poolId: string) =>
  api.put<AdminInnovationDetail & PictureFields>(
    `/admin/innovations/${slug}/picture`,
    { pool_id: poolId }
  );

export interface CheckedMark {
  volunteer_checked?: boolean;
  volunteer_reports?: number;
}

export async function listCheckedMarks(): Promise<Map<string, CheckedMark>> {
  const first = await api.get<Page<CheckedMark & { slug: string }>>(
    "/innovations",
    { page: 1, per_page: 100 }
  );
  const pages = Math.ceil(first.total / 100);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, pages - 1) }, (_, n) =>
      api.get<Page<CheckedMark & { slug: string }>>("/innovations", {
        page: n + 2,
        per_page: 100,
      })
    )
  );
  return new Map(
    [first, ...rest]
      .flatMap((p) => p.items)
      .map((i) => [
        i.slug,
        {
          volunteer_checked: i.volunteer_checked,
          volunteer_reports: i.volunteer_reports,
        },
      ])
  );
}
