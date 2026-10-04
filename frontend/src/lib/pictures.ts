import type { AdminInnovationDetail } from "$lib/api/admin";
import { api } from "$lib/api/client";

export interface PictureFields {
  image_alt?: string | null;
  image_card_url?: string | null;
  image_label?: string | null;
  image_source?: string | null;
  image_url?: string | null;
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
