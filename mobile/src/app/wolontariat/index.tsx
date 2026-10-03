import Head from "expo-router/head";
import { Check, ChevronDown, Search, X } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { Platform, Pressable, StyleSheet, type Text, View } from "react-native";
import type { InnovationSummary } from "@/api/types";
import { APP_NAME } from "@/config";
import { CategoryTile } from "@/features/category-icon";
import { VolunteerApply } from "@/features/volunteer";
import { useVolunteerSolutions } from "@/hooks/use-volunteer";
import { focusElement } from "@/lib/a11y";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const STEPS = [
  "Wybierasz rozwiązanie i piszesz, co chcesz z nim zrobić.",
  "Pracownik ROPS czyta zgłoszenie i odpisuje e-mailem.",
  "Po akcji opisujesz, jak poszło, w krótkim formularzu z linku w e-mailu.",
];

function Steps() {
  const { colors, wide } = useTheme();
  return (
    <View role="list" style={[styles.steps, wide && styles.stepsWide]}>
      {STEPS.map((step, index) => (
        <View
          key={step}
          role="listitem"
          style={[styles.step, wide && styles.stepWide]}
        >
          <Txt mono style={{ color: colors.stamp }} variant="h3">
            {index + 1}
          </Txt>
          <Txt style={styles.grow}>{step}</Txt>
        </View>
      ))}
    </View>
  );
}

function Solution({
  innovation,
  onSelect,
  selected,
}: {
  innovation: InnovationSummary;
  onSelect: () => void;
  selected: boolean;
}) {
  const { colors, highContrast } = useTheme();
  const Mark = selected ? Check : ChevronDown;
  return (
    <Pressable
      aria-expanded={selected}
      onPress={onSelect}
      role="button"
      style={[
        styles.solution,
        {
          backgroundColor: selected ? colors.tone : colors.paper,
          borderColor: highContrast || selected ? colors.stamp : colors.tone,
          borderWidth: highContrast ? 2 : 1.5,
        },
      ]}
    >
      <CategoryTile size={48} slug={innovation.category.slug} />
      <View style={styles.grow}>
        <Txt variant="lead" weight="600">
          {innovation.title}
        </Txt>
        <Txt tone="soft" variant="detail">
          {innovation.lead}
        </Txt>
      </View>
      <Mark aria-hidden color={colors.stamp} size={24} strokeWidth={2.2} />
    </Pressable>
  );
}

function Apply({
  innovation,
  onCancel,
}: {
  innovation: InnovationSummary;
  onCancel: () => void;
}) {
  const title = useRef<Text>(null);
  useEffect(() => {
    if (Platform.OS !== "web") {
      focusElement(title.current);
      return;
    }
    const element = title.current as unknown as HTMLElement | null;
    element?.setAttribute("tabindex", "-1");
    element?.focus({ preventScroll: true });
    element?.scrollIntoView({ block: "nearest" });
  }, []);
  return (
    <Sheet raised>
      <View style={styles.group}>
        <Txt tone="soft" variant="label">
          Zgłoszenie do rozwiązania
        </Txt>
        <Heading level={2} ref={title}>
          {innovation.title}
        </Heading>
      </View>
      <VolunteerApply onCancel={onCancel} slug={innovation.slug} />
    </Sheet>
  );
}

export default function VolunteerScreen() {
  const { wide } = useTheme();
  const {
    clear,
    draft,
    hasMore,
    list,
    loadMore,
    query,
    retry,
    search,
    setDraft,
  } = useVolunteerSolutions();
  const [selected, setSelected] = useState<string | null>(null);
  const empty = !(list.loading || list.error) && list.items.length === 0;

  return (
    <Screen
      back="Działaj"
      backFallback="/dzialaj"
      title="Zostań wolontariuszem"
      width={900}
    >
      <Head>
        <title>{`Wolontariat · ${APP_NAME}`}</title>
        <meta
          content="Wypróbuj rozwiązanie z biblioteki ROPS w swojej okolicy jako wolontariusz."
          name="description"
        />
      </Head>

      <View style={styles.group}>
        <Txt variant="lead">
          Wolontariusz wypróbowuje gotowe rozwiązanie z biblioteki ROPS u
          siebie: w klubie seniora, szkole, parafii albo organizacji. Nie
          zakładasz konta.
        </Txt>
        <Steps />
      </View>

      <View style={[styles.group, styles.pick]}>
        <Heading level={2}>Wybierz rozwiązanie</Heading>
        <View style={[styles.search, wide && styles.searchWide]}>
          <View style={styles.grow}>
            <TextField
              enterKeyHint="search"
              hideLabel
              label="Szukaj rozwiązania"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="np. seniorzy, opieka, młodzież"
              returnKeyType="search"
              value={draft}
            />
          </View>
          <View style={styles.buttons}>
            <Button
              icon={Search}
              label="Szukaj"
              onPress={search}
              style={styles.tall}
              variant="primary"
            />
            {query ? (
              <Button
                icon={X}
                label="Wyczyść"
                onPress={clear}
                style={styles.tall}
                variant="quiet"
              />
            ) : null}
          </View>
        </View>
      </View>

      <View aria-live="polite" style={styles.group}>
        {list.loading && list.items.length === 0 ? (
          <Txt tone="soft">Wczytuję rozwiązania.</Txt>
        ) : null}
        {list.error ? (
          <Notice title="Nie udało się wczytać rozwiązań" tone="error">
            <View style={styles.group}>
              <Txt>{list.error}</Txt>
              <Button label="Spróbuj ponownie" onPress={retry} />
            </View>
          </Notice>
        ) : null}
        {empty ? (
          <Txt>
            Nie znaleźliśmy rozwiązania dla tych słów. Spróbuj krócej albo
            wyczyść wyszukiwanie.
          </Txt>
        ) : null}
      </View>

      {list.items.length > 0 ? (
        <View role="list" style={styles.list}>
          {list.items.map((innovation) => {
            const open = selected === innovation.slug;
            return (
              <View key={innovation.slug} role="listitem" style={styles.list}>
                <Solution
                  innovation={innovation}
                  onSelect={() => setSelected(open ? null : innovation.slug)}
                  selected={open}
                />
                {open ? (
                  <Apply
                    innovation={innovation}
                    onCancel={() => setSelected(null)}
                  />
                ) : null}
              </View>
            );
          })}
        </View>
      ) : null}

      {hasMore ? (
        <Button
          busy={list.loading}
          label={list.loading ? "Wczytuję" : "Pokaż więcej rozwiązań"}
          onPress={loadMore}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  buttons: {
    flexDirection: "row",
    gap: space.sm,
  },
  group: {
    gap: space.md,
  },
  grow: {
    flex: 1,
    gap: space.xs,
  },
  list: {
    gap: space.sm,
  },
  pick: {
    marginTop: space.lg,
  },
  search: {
    gap: space.md,
  },
  searchWide: {
    alignItems: "stretch",
    flexDirection: "row",
  },
  solution: {
    alignItems: "center",
    borderRadius: radius.lg + 4,
    flexDirection: "row",
    gap: space.lg,
    minHeight: minTarget,
    padding: space.lg,
  },
  step: {
    alignItems: "baseline",
    flexDirection: "row",
    gap: space.md,
  },
  steps: {
    gap: space.sm,
  },
  stepsWide: {
    flexDirection: "row",
    gap: space.xl,
  },
  stepWide: {
    flex: 1,
  },
  tall: {
    alignSelf: "stretch",
    minHeight: 62,
  },
});
