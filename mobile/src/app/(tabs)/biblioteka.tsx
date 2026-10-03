import { router } from "expo-router";
import Head from "expo-router/head";
import { Compass, FileText, Search, X } from "lucide-react-native";
import { ScrollView, StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { categoryIcon } from "@/features/category-icon";
import { CardGrid, InnovationCard } from "@/features/innovation-card";
import { useLibrary } from "@/hooks/use-library";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { AccessButton } from "@/ui/shell";
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
    <Screen tabs trailing={<AccessButton />} width={900}>
      <Head>
        <title>{`Biblioteka innowacji · ${APP_NAME}`}</title>
      </Head>
      <PageHead>
        <Heading level={1}>Biblioteka innowacji</Heading>
        <View style={[styles.search, wide && styles.searchWide]}>
          <View style={styles.searchField}>
            <TextField
              enterKeyHint="search"
              hideLabel
              label="Szukaj w bibliotece"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="np. opieka wytchnieniowa"
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
          <ScrollView
            aria-label="Kategorie"
            contentContainerStyle={wide ? styles.categories : styles.strip}
            horizontal={!wide}
            role="group"
            showsHorizontalScrollIndicator={false}
            style={wide ? undefined : styles.bleed}
          >
            {categories.map((item) => (
              <Button
                icon={categoryIcon(item.slug)}
                key={item.slug}
                label={`${item.name} (${item.count})`}
                onPress={() => selectCategory(item.slug)}
                pressed={item.slug === category}
              />
            ))}
          </ScrollView>
        ) : null}
      </PageHead>

      <View style={styles.more}>
        <Button
          icon={Compass}
          label="Wyzwania Małopolski"
          onPress={() => router.push("/wiedza")}
          role="link"
          variant="quiet"
        />
        <Button
          icon={FileText}
          label="Raporty i materiały"
          onPress={() => router.push("/materialy")}
          role="link"
          variant="quiet"
        />
      </View>

      <View style={styles.results}>
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
          <CardGrid>
            {list.items.map((item) => (
              <InnovationCard innovation={item} key={item.slug} />
            ))}
          </CardGrid>
        ) : null}
        {hasMore ? (
          <Button
            busy={list.loading}
            label={list.loading ? "Wczytuję" : "Pokaż więcej"}
            onPress={loadMore}
          />
        ) : null}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  bleed: {
    marginHorizontal: -(space.xl - 2),
  },
  categories: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  errorBody: {
    gap: space.md,
  },
  more: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  results: {
    gap: space.lg,
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
  strip: {
    gap: space.sm,
    paddingHorizontal: space.xl - 2,
  },
  tall: {
    minHeight: minTarget + 8,
  },
});
