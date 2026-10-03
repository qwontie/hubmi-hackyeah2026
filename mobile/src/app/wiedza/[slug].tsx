import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { FileText } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { InnovationRow } from "@/features/innovation-row";
import { FigureView, MaterialRow } from "@/features/knowledge";
import { RichText } from "@/features/rich-text";
import { AI_CHALLENGE_NOTE, useChallenge } from "@/hooks/use-knowledge";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function ChallengeScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { state, retry } = useChallenge(slug);
  return (
    <Screen back="Wyzwania" backFallback="/wiedza">
      {state.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję opis wyzwania.
        </Txt>
      ) : null}
      {state.kind === "error" ? (
        <Notice
          title={
            state.missing ? "Nie ma takiego wyzwania" : "Nie udało się wczytać"
          }
          tone="error"
        >
          <View style={styles.group}>
            <Txt>{state.message}</Txt>
            {state.missing ? null : (
              <Button label="Spróbuj ponownie" onPress={retry} />
            )}
          </View>
        </Notice>
      ) : null}
      {state.kind === "done" ? (
        <>
          <Head>
            <title>{`${state.data.title} · ${APP_NAME}`}</title>
          </Head>
          <Sheet raised>
            <View style={styles.group}>
              <Heading level={1}>{state.data.title}</Heading>
              <Txt tone="soft" variant="detail">
                {state.data.area.name}
              </Txt>
            </View>
            {state.data.description ? (
              <RichText source={state.data.description} />
            ) : (
              <Txt>{state.data.summary}</Txt>
            )}
            {state.data.verified ? null : (
              <Txt tone="soft" variant="detail">
                {AI_CHALLENGE_NOTE}
              </Txt>
            )}
            <ExternalLink
              href={state.data.source.url}
              icon={FileText}
              label={`Dokument źródłowy: ${state.data.source.title}`}
            />
          </Sheet>

          {state.data.figures.length > 0 ? (
            <Sheet>
              <Heading level={2}>Liczby</Heading>
              <View style={styles.group}>
                {state.data.figures.map((figure) => (
                  <FigureView
                    figure={figure}
                    key={`${figure.label}-${figure.page}`}
                  />
                ))}
              </View>
            </Sheet>
          ) : null}

          {state.data.related_innovations.length > 0 ? (
            <Sheet>
              <Heading level={2}>Gotowe rozwiązania z biblioteki ROPS</Heading>
              <View role="list">
                {state.data.related_innovations.map((item, index) => (
                  <InnovationRow
                    innovation={item}
                    key={item.slug}
                    last={index === state.data.related_innovations.length - 1}
                  />
                ))}
              </View>
            </Sheet>
          ) : null}

          {state.data.related_materials.length > 0 ? (
            <Sheet>
              <Heading level={2}>Przeczytaj więcej</Heading>
              <View role="list">
                {state.data.related_materials.map((item, index) => (
                  <MaterialRow
                    key={item.id}
                    last={index === state.data.related_materials.length - 1}
                    material={item}
                  />
                ))}
              </View>
            </Sheet>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  group: {
    gap: space.md,
  },
});
