import Head from "expo-router/head";
import { Search, X } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { MaterialRow } from "@/features/knowledge";
import { useMaterials } from "@/hooks/use-knowledge";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function MaterialsScreen() {
  const { wide } = useTheme();
  const {
    clearSearch,
    draft,
    hasMore,
    kind,
    kinds,
    list,
    loadMore,
    query,
    retry,
    search,
    selectKind,
    selectTopic,
    setDraft,
    topic,
    topics,
  } = useMaterials();

  return (
    <Screen back="Biblioteka" backFallback="/biblioteka" width={900}>
      <Head>
        <title>{`Raporty i materiały ROPS · ${APP_NAME}`}</title>
      </Head>
      <Sheet raised>
        <Heading level={1}>Raporty i materiały ROPS</Heading>
        <View style={[styles.group, wide && styles.searchWide]}>
          <View style={styles.flex}>
            <TextField
              enterKeyHint="search"
              label="Szukaj w materiałach"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="Na przykład: piecza zastępcza"
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
        {kinds.length > 0 ? (
          <View aria-label="Rodzaj materiału" role="group" style={styles.chips}>
            {kinds.map((item) => (
              <Button
                key={item.slug}
                label={`${item.name} (${item.count})`}
                onPress={() => selectKind(item.slug)}
                pressed={item.slug === kind}
              />
            ))}
          </View>
        ) : null}
        {topics.length > 0 ? (
          <Select
            emptyLabel="Wszystkie tematy"
            label="Temat"
            onChange={selectTopic}
            options={topics.map((item) => ({
              label: `${item.name} (${item.count})`,
              value: item.slug,
            }))}
            value={topic}
          />
        ) : null}
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
              : `${list.total} ${pluralPl(list.total, "materiał", "materiały", "materiałów")}`}
          </Txt>
        )}
        {!(list.loading || list.error) && list.items.length === 0 ? (
          <Txt>Nie znaleźliśmy materiału. Spróbuj innego słowa.</Txt>
        ) : null}
        {list.items.length > 0 ? (
          <View role="list">
            {list.items.map((item, index) => (
              <MaterialRow
                key={item.id}
                last={index === list.items.length - 1}
                material={item}
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
