import { Play } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { ExternalLink } from "@/ui/external-link";

const YOUTUBE =
  /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/;

export const youtubeId = (url: string) => {
  const match = url.match(YOUTUBE);
  return match?.[1] ?? null;
};

export function Video({ url, title }: { url: string; title: string }) {
  const { colors } = useTheme();
  const id = youtubeId(url);
  return (
    <View style={styles.wrap}>
      {id ? (
        <View style={[styles.frame, { backgroundColor: colors.sunk }]}>
          <iframe
            allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
            allowFullScreen
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            src={`https://www.youtube-nocookie.com/embed/${id}?rel=0&hl=pl&cc_lang_pref=pl`}
            style={{ border: 0, height: "100%", width: "100%" }}
            title={`Film: ${title}`}
          />
        </View>
      ) : null}
      <ExternalLink
        href={url}
        icon={Play}
        label={
          id
            ? "Otwórz film w serwisie YouTube"
            : "Obejrzyj film w serwisie YouTube"
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    aspectRatio: 16 / 9,
    borderRadius: radius.lg,
    overflow: "hidden",
    width: "100%",
  },
  wrap: {
    gap: space.md,
  },
});
