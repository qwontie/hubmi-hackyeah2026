import { Play } from "lucide-react-native";
import { ExternalLink } from "@/ui/external-link";

const YOUTUBE =
  /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/;

export const youtubeId = (url: string) => {
  const match = url.match(YOUTUBE);
  return match?.[1] ?? null;
};

export function Video({ url }: { url: string; title: string }) {
  return (
    <ExternalLink
      href={url}
      icon={Play}
      label="Obejrzyj film w serwisie YouTube"
    />
  );
}
