import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { Download, Landmark } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { InnovationRow } from "@/features/innovation-row";
import { ChallengeRow } from "@/features/knowledge";
import { ReadAloudButton } from "@/features/read-aloud-button";
import { AI_SUMMARY_NOTE, fileLabel, useMaterial } from "@/hooks/use-knowledge";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function MaterialScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { state, retry } = useMaterial(id);
  return (
    <Screen back="Materiały" backFallback="/materialy">
      {state.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję opis materiału…
        </Txt>
      ) : null}
      {state.kind === "error" ? (
        <Notice
          title={
            state.missing ? "Nie ma takiego materiału" : "Nie udało się wczytać"
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
                {[
                  state.data.kind.name,
                  state.data.year ? String(state.data.year) : null,
                  state.data.topics.map((item) => item.name).join(", ") || null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </Txt>
            </View>
            {state.data.summary ? (
              <>
                <Txt variant="lead">{state.data.summary}</Txt>
                {state.data.summary_ai ? (
                  <Txt tone="soft" variant="detail">
                    {AI_SUMMARY_NOTE}
                  </Txt>
                ) : null}
                <ReadAloudButton
                  text={`${state.data.title}. ${state.data.summary}`}
                />
              </>
            ) : null}
            <View style={styles.group}>
              <ExternalLink
                description={`(${fileLabel(state.data)})`}
                href={state.data.file_url}
                icon={Download}
                label="Pobierz dokument"
              />
              <ExternalLink
                href={state.data.source_url}
                icon={Landmark}
                label="Zobacz na stronie ROPS w Krakowie"
              />
            </View>
          </Sheet>

          {state.data.related_challenges.length > 0 ? (
            <Sheet>
              <Heading level={2}>Wyzwania, których dotyczy</Heading>
              <View role="list">
                {state.data.related_challenges.map((item, index) => (
                  <ChallengeRow
                    challenge={item}
                    key={item.id}
                    last={index === state.data.related_challenges.length - 1}
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
