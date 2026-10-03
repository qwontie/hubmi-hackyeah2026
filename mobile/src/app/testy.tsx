import Head from "expo-router/head";
import { Check, FlaskConical } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import type { InnovationSummary } from "@/api/types";
import { APP_NAME } from "@/config";
import { TestSignupBlock } from "@/features/tester";
import { useTestOpportunities } from "@/hooks/use-test-opportunities";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

function Opportunity({
  innovation,
  selected,
  onSelect,
}: {
  innovation: InnovationSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  const { colors } = useTheme();
  return (
    <Pressable
      aria-pressed={selected}
      onPress={onSelect}
      role="button"
      style={[
        styles.opportunity,
        {
          backgroundColor: selected ? colors.tone : colors.paper,
          borderColor: selected ? colors.stamp : colors.ruleStrong,
        },
      ]}
    >
      <View style={styles.opportunityText}>
        <Txt weight="600">{innovation.title}</Txt>
        <Txt tone="soft" variant="label">
          {innovation.lead}
        </Txt>
      </View>
      {selected ? (
        <Check aria-hidden color={colors.stamp} size={24} strokeWidth={2.5} />
      ) : (
        <FlaskConical aria-hidden color={colors.stamp} size={24} />
      )}
    </Pressable>
  );
}

export default function TestingScreen() {
  const { list, hasMore, loadMore, retry } = useTestOpportunities();
  const [selected, setSelected] = useState<InnovationSummary | null>(null);

  return (
    <Screen back="Wróć" width={900}>
      <Head>
        <title>{`Testuj innowacje · ${APP_NAME}`}</title>
        <meta
          content="Zgłoś się do testowania innowacji społecznych z biblioteki ROPS."
          name="description"
        />
      </Head>

      <View style={styles.group}>
        <Heading level={1}>Testuj innowacje społeczne</Heading>
        <Txt tone="soft" variant="lead">
          Wybierz rozwiązanie z biblioteki ROPS i zostaw kontakt. ROPS odezwie
          się, gdy będzie można dołączyć do testów.
        </Txt>
      </View>

      {list.loading && list.items.length === 0 ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję rozwiązania otwarte na zgłoszenia.
        </Txt>
      ) : null}

      {list.error ? (
        <Notice title="Nie udało się wczytać rozwiązań" tone="error">
          <View style={styles.group}>
            <Txt>{list.error}</Txt>
            <Button label="Spróbuj ponownie" onPress={retry} />
          </View>
        </Notice>
      ) : null}

      {list.items.length > 0 ? (
        <View role="list" style={styles.list}>
          {list.items.map((innovation) => (
            <View key={innovation.slug} role="listitem">
              <Opportunity
                innovation={innovation}
                onSelect={() => setSelected(innovation)}
                selected={selected?.slug === innovation.slug}
              />
            </View>
          ))}
        </View>
      ) : null}

      {hasMore ? (
        <Button
          busy={list.loading}
          label={list.loading ? "Wczytuję" : "Pokaż więcej"}
          onPress={loadMore}
        />
      ) : null}

      {selected ? (
        <Sheet aria-live="polite" raised>
          <View style={styles.group}>
            <Txt tone="soft" variant="label">
              Wybrane rozwiązanie
            </Txt>
            <Heading level={2}>{selected.title}</Heading>
          </View>
          <TestSignupBlock key={selected.slug} slug={selected.slug} />
        </Sheet>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  group: {
    gap: space.md,
  },
  list: {
    gap: space.sm,
  },
  opportunity: {
    alignItems: "center",
    borderRadius: radius.lg,
    borderWidth: 1.5,
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget,
    padding: space.lg,
  },
  opportunityText: {
    flex: 1,
    gap: space.xs,
  },
});
