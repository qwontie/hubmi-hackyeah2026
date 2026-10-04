import { Play } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { ExternalLink } from "@/ui/external-link";
import { Txt } from "@/ui/text";

const YOUTUBE =
  /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([\w-]{11})/;

export const youtubeId = (url: string) => {
  const match = url.match(YOUTUBE);
  return match?.[1] ?? null;
};

export function Video({ url, title }: { url: string; title: string }) {
  const { colors } = useTheme();
  const id = youtubeId(url);
  const [playing, setPlaying] = useState(false);
  return (
    <View style={styles.wrap}>
      {id ? (
        <View style={[styles.frame, { backgroundColor: colors.night }]}>
          {playing ? (
            <iframe
              allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
              allowFullScreen
              loading="lazy"
              referrerPolicy="strict-origin-when-cross-origin"
              src={`https://www.youtube-nocookie.com/embed/${id}?rel=0&hl=pl&cc_lang_pref=pl&autoplay=1`}
              style={{ border: 0, height: "100%", width: "100%" }}
              title={`Film: ${title}`}
            />
          ) : (
            <Pressable
              aria-label={`Odtwórz film: ${title}`}
              onPress={() => setPlaying(true)}
              role="button"
              style={styles.cover}
            >
              <View style={[styles.play, { borderColor: colors.onNight }]}>
                <Play aria-hidden color={colors.onNight} size={32} />
              </View>
              <Txt tone="onNight" weight="600">
                Odtwórz film
              </Txt>
              <Txt style={styles.center} tone="onNightSoft" variant="detail">
                Film wczyta się z serwisu YouTube dopiero po kliknięciu.
              </Txt>
            </Pressable>
          )}
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
  center: {
    textAlign: "center",
  },
  cover: {
    alignItems: "center",
    flex: 1,
    gap: space.sm,
    justifyContent: "center",
    padding: space.lg,
  },
  frame: {
    aspectRatio: 16 / 9,
    borderRadius: radius.lg,
    overflow: "hidden",
    width: "100%",
  },
  play: {
    alignItems: "center",
    borderRadius: 999,
    borderWidth: 2,
    height: 64,
    justifyContent: "center",
    width: 64,
  },
  wrap: {
    gap: space.md,
  },
});
