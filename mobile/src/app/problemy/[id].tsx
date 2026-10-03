import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { Lightbulb } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { CategoryTile } from "@/features/category-icon";
import { CardGrid, InnovationCard } from "@/features/innovation-card";
import { useDemo } from "@/hooks/use-demo";
import {
  PROBLEM_SUMMARY_NOTE,
  problemStats,
  useProblem,
} from "@/hooks/use-problems";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function ProblemScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const { state, retry, propose } = useProblem(id);
  const demo = useDemo();

  const hero =
    state.kind === "done" ? (
      <View style={styles.group}>
        <CategoryTile size={64} slug={state.data.category?.slug} />
        <Heading level={1}>{state.data.title}</Heading>
        <Txt tone="soft" variant="lead">
          {state.data.summary}
        </Txt>
        <Txt tone="soft" variant="detail" weight="500">
          {problemStats(state.data, demo).replaceAll(" · ", "\u00a0· ")}
        </Txt>
        <Txt tone="soft" variant="small">
          {PROBLEM_SUMMARY_NOTE}
        </Txt>
        <View>
          <Button
            icon={Lightbulb}
            label="Zaproponuj rozwiązanie"
            onPress={propose}
            size="large"
            variant="primary"
          />
        </View>
      </View>
    ) : undefined;

  return (
    <Screen back="Problemy" backFallback="/pomysl" hero={hero} width={900}>
      {state.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję opis problemu.
        </Txt>
      ) : null}

      {state.kind === "error" ? (
        <Notice
          title={
            state.missing
              ? "Nie ma takiego problemu"
              : "Nie udało się wczytać problemu"
          }
          tone="error"
        >
          <View style={styles.group}>
            <Txt>
              {state.missing
                ? "Pokazujemy tylko problemy, które zgłosiły co najmniej 3 osoby."
                : state.message}
            </Txt>
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
          {state.data.innovations.length > 0 ? (
            <View style={styles.section}>
              <Heading level={2}>Co już działa w Małopolsce</Heading>
              <CardGrid>
                {state.data.innovations.map((innovation) => (
                  <InnovationCard
                    innovation={innovation}
                    key={innovation.slug}
                  />
                ))}
              </CardGrid>
            </View>
          ) : null}
          <View style={styles.section}>
            <Heading level={2}>Pomysły mieszkańców</Heading>
            {state.data.ideas.length === 0 ? (
              <Txt tone="soft">
                Nikt jeszcze nie zaproponował rozwiązania. Twój pomysł może być
                pierwszy.
              </Txt>
            ) : (
              <Sheet>
                <View role="list">
                  {state.data.ideas.map((idea, index) => (
                    <View
                      key={idea.id}
                      role="listitem"
                      style={[
                        styles.idea,
                        index > 0 && {
                          borderTopColor: colors.rule,
                          borderTopWidth: 1,
                        },
                      ]}
                    >
                      <Txt weight="600">{idea.title}</Txt>
                      <Txt tone="soft" variant="label">
                        {idea.essence}
                      </Txt>
                    </View>
                  ))}
                </View>
              </Sheet>
            )}
          </View>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  group: {
    gap: space.md,
  },
  idea: {
    gap: space.xs,
    paddingVertical: space.md,
  },
  section: {
    gap: space.lg,
    marginTop: space.sm,
  },
});
