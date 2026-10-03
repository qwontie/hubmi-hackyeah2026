import { router } from "expo-router";
import Head from "expo-router/head";
import { FileText, Search, X } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { ChallengeRow } from "@/features/knowledge";
import { useChallenges } from "@/hooks/use-knowledge";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function ChallengesScreen() {
  const { wide } = useTheme();
  const {
    area,
    areas,
    clearSearch,
    draft,
    hasMore,
    list,
    loadMore,
    query,
    retry,
    search,
    selectArea,
    setDraft,
  } = useChallenges();

  return (
    <Screen width={900}>
      <Head>
        <title>{`Wyzwania Małopolski · ${APP_NAME}`}</title>
      </Head>
      <Sheet raised>
        <View style={styles.group}>
          <Heading level={1}>Wyzwania społeczne Małopolski</Heading>
          <Txt tone="soft" variant="lead">
            Najważniejsze problemy regionu według raportów ROPS w Krakowie,
            każdy z liczbami i źródłem.
          </Txt>
        </View>
        <View style={[styles.group, wide && styles.searchWide]}>
          <View style={styles.flex}>
            <TextField
              enterKeyHint="search"
              label="Szukaj wyzwania"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="Na przykład: samotność seniorów"
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
                onPress={clearSearch}
                style={styles.tall}
                variant="quiet"
              />
            ) : null}
          </View>
        </View>
        {areas.length > 0 ? (
          <View aria-label="Obszary" role="group" style={styles.chips}>
            {areas.map((item) => (
              <Button
                key={item.slug}
                label={`${item.name} (${item.count})`}
                onPress={() => selectArea(item.slug)}
                pressed={item.slug === area}
              />
            ))}
          </View>
        ) : null}
        <Button
          icon={FileText}
          label="Raporty i materiały ROPS"
          onPress={() => router.push("/materialy")}
          variant="quiet"
        />
      </Sheet>

      <Sheet>
        {list.error ? (
          <Notice tone="error">
            <View style={styles.group}>
              <Txt>{list.error}</Txt>
              <Button label="Spróbuj ponownie" onPress={retry} />
            </View>
          </Notice>
        ) : (
          <Txt aria-live="polite" tone="soft" weight="500">
            {list.loading && list.items.length === 0
              ? "Wczytuję…"
              : `${list.total} ${pluralPl(list.total, "wyzwanie", "wyzwania", "wyzwań")}`}
          </Txt>
        )}
        {!(list.loading || list.error) && list.items.length === 0 ? (
          <Txt>Nie znaleźliśmy wyzwania. Spróbuj innego słowa.</Txt>
        ) : null}
        {list.items.length > 0 ? (
          <View role="list">
            {list.items.map((item, index) => (
              <ChallengeRow
                challenge={item}
                key={item.id}
                last={index === list.items.length - 1}
              />
            ))}
          </View>
        ) : null}
        {hasMore ? (
          <Button
            busy={list.loading}
            label={list.loading ? "Wczytuję…" : "Pokaż więcej"}
            onPress={loadMore}
          />
        ) : null}
      </Sheet>
    </Screen>
  );
}

const styles = StyleSheet.create({
  buttons: {
    flexDirection: "row",
    gap: space.sm,
  },
  chips: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  flex: {
    flex: 1,
  },
  group: {
    gap: space.md,
  },
  searchWide: {
    alignItems: "flex-end",
    flexDirection: "row",
  },
  tall: {
    minHeight: minTarget + 8,
  },
});
