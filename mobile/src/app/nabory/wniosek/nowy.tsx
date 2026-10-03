import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { ArrowRight } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { useApplicationCreate } from "@/hooks/use-grants";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { Heading, Txt } from "@/ui/text";

function Choice({
  onPress,
  text,
  title,
}: {
  onPress: () => void;
  text: string;
  title: string;
}) {
  const { colors, highContrast } = useTheme();
  const [hot, setHot] = useState(false);
  return (
    <Pressable
      onHoverIn={() => setHot(true)}
      onHoverOut={() => setHot(false)}
      onPress={onPress}
      role="button"
      style={[
        styles.choice,
        {
          backgroundColor: hot ? colors.tone : colors.paper,
          borderColor: highContrast ? colors.ink : colors.tone,
          borderWidth: highContrast ? 2 : 1,
        },
      ]}
    >
      <View style={styles.words}>
        <Txt variant="lead" weight="600">
          {title}
        </Txt>
        <Txt tone="soft">{text}</Txt>
      </View>
      <View style={styles.fixed}>
        <ArrowRight aria-hidden color={colors.stamp} size={26} />
      </View>
    </Pressable>
  );
}

export default function NewApplicationScreen() {
  const { nabor, pomysl } = useLocalSearchParams<{
    nabor?: string;
    pomysl?: string;
  }>();
  const { create, retry, state } = useApplicationCreate(nabor, pomysl);
  return (
    <Screen back="Nabory" backFallback="/nabory">
      <Head>
        <title>{`Nowy wniosek · ${APP_NAME}`}</title>
      </Head>
      {state.kind === "working" ? (
        <Txt aria-live="polite">Otwieram formularz wniosku.</Txt>
      ) : null}
      {state.kind === "error" ? (
        <Notice title="Nie udało się otworzyć wniosku" tone="error">
          <View style={styles.group}>
            <Txt>{state.message}</Txt>
            <Button label="Spróbuj ponownie" onPress={retry} />
          </View>
        </Notice>
      ) : null}
      {state.kind === "choose" ? (
        <>
          <PageHead>
            <View style={styles.group}>
              <Heading level={1}>Czy wniosek dotyczy Twojego pomysłu?</Heading>
              <Txt tone="soft" variant="lead">
                Jeśli tak, skopiujemy odpowiedzi z pomysłu. Każdą z nich
                poprawisz przed wysłaniem.
              </Txt>
            </View>
          </PageHead>
          <View style={styles.group}>
            {state.ideas.map((idea) => (
              <Choice
                key={idea.id}
                onPress={() => create(idea)}
                text="Skopiujemy odpowiedzi z tego pomysłu."
                title={`Tak: ${idea.title}`}
              />
            ))}
            <Choice
              onPress={() => create(null)}
              text="Odpowiesz na pytania od początku."
              title="Nie, zacznę od pustego formularza"
            />
          </View>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  choice: {
    alignItems: "center",
    borderRadius: radius.sheet,
    flexDirection: "row",
    gap: space.lg,
    justifyContent: "space-between",
    minHeight: minTarget,
    paddingHorizontal: space.xl,
    paddingVertical: space.lg + 2,
  },
  fixed: { flexShrink: 0 },
  group: { gap: space.md },
  words: { flexShrink: 1, gap: space.xs },
});
