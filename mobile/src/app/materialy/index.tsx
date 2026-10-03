import Head from "expo-router/head";
import { Search, X } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { CategoryFilter } from "@/features/category-filter";
import { MaterialRow } from "@/features/knowledge";
import { TopicFilter } from "@/features/topic-filter";
import { useMaterials } from "@/hooks/use-knowledge";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Txt } from "@/ui/text";

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
    <Screen
      back="Biblioteka"
      backFallback="/biblioteka"
      title="Raporty i materiały ROPS"
      width={900}
    >
      <Head>
        <title>{`Raporty i materiały ROPS · ${APP_NAME}`}</title>
      </Head>
      <PageHead>
        <View style={[styles.group, wide && styles.searchWide]}>
          <View style={styles.flex}>
            <TextField
              enterKeyHint="search"
              hideLabel
              label="Szukaj w materiałach"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="np. piecza zastępcza"
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
        <CategoryFilter
          items={kinds}
          label="Rodzaj materiału"
          onSelect={selectKind}
          value={kind}
        />
        <TopicFilter
          emptyLabel="Wszystkie tematy"
          items={topics}
          label="Temat"
          onSelect={selectTopic}
          value={topic}
        />
      </PageHead>

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
              ? "Wczytuję"
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
            label={list.loading ? "Wczytuję" : "Pokaż więcej"}
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
  flex: {
    flex: 1,
  },
  group: {
    gap: space.md,
  },
  searchWide: {
    alignItems: "stretch",
    flexDirection: "row",
  },
  tall: {
    alignSelf: "stretch",
    minHeight: 62,
  },
});
