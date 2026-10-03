import { Image } from "expo-image";
import { Sparkles } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { API_BASE } from "@/config";
import { useIdeaVisualisation } from "@/hooks/use-idea-visualisation";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const absolute = (url: string) =>
  url.startsWith("/") ? `${API_BASE}${url}` : url;

export function IdeaVisualisation({ id }: { id: string | undefined }) {
  const { colors, reduceMotion } = useTheme();
  const { error, generate, generating, idea } = useIdeaVisualisation(id);
  if (!idea) {
    return null;
  }
  const left = idea.visualisations_left;
  return (
    <Sheet>
      <View style={styles.group}>
        <Heading level={2}>Ilustracja pomysłu</Heading>
        {idea.visualisation_url ? (
          <View style={[styles.frame, { backgroundColor: colors.tone }]}>
            <Image
              accessibilityLabel={
                idea.visualisation_alt ?? "Ilustracja pomysłu"
              }
              contentFit="cover"
              source={{ uri: absolute(idea.visualisation_url) }}
              style={styles.image}
              transition={reduceMotion ? 0 : 240}
            />
          </View>
        ) : (
          <Txt tone="soft">
            Sztuczna inteligencja narysuje prostą ilustrację na podstawie opisu
            pomysłu. Zobaczy ją też pracownik ROPS.
          </Txt>
        )}
      </View>
      <View aria-live="polite" style={styles.group}>
        {error ? (
          <Txt tone="bad" weight="500">
            {error}
          </Txt>
        ) : null}
        {left > 0 ? (
          <Button
            busy={generating}
            icon={Sparkles}
            label={pickLabel(generating, Boolean(idea.visualisation_url))}
            onPress={() => {
              generate().catch(() => undefined);
            }}
          />
        ) : null}
        {idea.visualisation_url ? (
          <Txt tone="soft" variant="small">
            {`Ilustracja wygenerowana przez AI. Zostało prób: ${left}.`}
          </Txt>
        ) : null}
      </View>
    </Sheet>
  );
}

const pickLabel = (generating: boolean, exists: boolean) => {
  if (generating) {
    return "Rysuję ilustrację";
  }
  return exists ? "Narysuj inną" : "Narysuj ilustrację";
};

const styles = StyleSheet.create({
  frame: {
    aspectRatio: 4 / 3,
    borderRadius: 22,
    maxWidth: 560,
    overflow: "hidden",
    width: "100%",
  },
  group: {
    gap: space.md,
  },
  image: {
    height: "100%",
    width: "100%",
  },
});
