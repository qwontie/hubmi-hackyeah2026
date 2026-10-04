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
