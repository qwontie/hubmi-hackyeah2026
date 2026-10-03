import Head from "expo-router/head";
import { Search, X } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { InnovationRow } from "@/features/innovation-row";
import { useLibrary } from "@/hooks/use-library";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function LibraryScreen() {
  const { wide } = useTheme();
  const {
    categories,
    category,
    clearSearch,
    draft,
    hasMore,
    list,
    loadMore,
    query,
    retry,
    search,
    selectCategory,
    setDraft,
    summary,
  } = useLibrary();

  return (
    <Screen width={900}>
      <Head>
        <title>{`Biblioteka innowacji · ${APP_NAME}`}</title>
      </Head>
      <Sheet raised>
        <Heading level={1}>Biblioteka innowacji</Heading>
        <View style={[styles.search, wide && styles.searchWide]}>
          <View style={styles.searchField}>
            <TextField
              enterKeyHint="search"
              label="Szukaj w bibliotece"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="Na przykład: opieka wytchnieniowa"
              returnKeyType="search"
              value={draft}
            />
          </View>
          <View style={styles.searchButtons}>
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
        {categories.length > 0 ? (
          <View aria-label="Kategorie" role="group" style={styles.categories}>
            {categories.map((item) => (
              <Button
                key={item.slug}
                label={`${item.name} (${item.count})`}
                onPress={() => selectCategory(item.slug)}
                pressed={item.slug === category}
              />
            ))}
          </View>
        ) : null}
      </Sheet>

      <Sheet>
        {list.error ? null : (
          <Txt aria-live="polite" tone="soft" weight="500">
            {summary}
          </Txt>
        )}
        {list.error ? (
          <Notice tone="error">
            <View style={styles.errorBody}>
              <Txt>{list.error}</Txt>
              <Button label="Spróbuj ponownie" onPress={retry} />
            </View>
          </Notice>
        ) : null}
        {!list.loading && list.items.length === 0 && !list.error ? (
          <Txt>
            Nic nie znaleźliśmy. Spróbuj innego słowa albo opisz problem na
            stronie głównej, a dopasujemy rozwiązania do Twojej sytuacji.
          </Txt>
        ) : null}
        {list.items.length > 0 ? (
          <View role="list">
            {list.items.map((item, index) => (
              <InnovationRow
                innovation={item}
                key={item.slug}
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
  categories: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  errorBody: {
    gap: space.md,
  },
  search: {
    gap: space.md,
  },
  searchButtons: {
    flexDirection: "row",
    gap: space.sm,
  },
  searchField: {
    flex: 1,
  },
  searchWide: {
    alignItems: "flex-end",
    flexDirection: "row",
  },
  tall: {
    minHeight: minTarget + 8,
  },
});
