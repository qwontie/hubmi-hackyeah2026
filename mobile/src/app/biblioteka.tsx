import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { Search, X } from "lucide-react-native";
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { api, errorMessage } from "@/api/client";
import type { Category, InnovationSummary } from "@/api/types";
import { APP_NAME } from "@/config";
import { InnovationRow } from "@/features/innovation-row";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const PER_PAGE = 20;

interface ListState {
  error: string | null;
  items: InnovationSummary[];
  loading: boolean;
  page: number;
  total: number;
}

const emptyList: ListState = {
  error: null,
  items: [],
  loading: true,
  page: 0,
  total: 0,
};

export default function LibraryScreen() {
  const params = useLocalSearchParams<{ kategoria?: string; q?: string }>();
  const category = params.kategoria ?? "";
  const query = params.q ?? "";
  const { wide } = useTheme();
  const [categories, setCategories] = useState<Category[]>([]);
  const [draft, setDraft] = useState(query);
  const [list, setList] = useState<ListState>(emptyList);
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const abort = new AbortController();
    api
      .categories(abort.signal)
      .then(setCategories)
      .catch(() => setCategories([]));
    return () => abort.abort();
  }, []);

  useEffect(() => {
    setDraft(query);
    setPage(1);
  }, [query]);

  useEffect(() => {
    if (attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setList((current) => ({
      ...(page === 1 ? emptyList : current),
      error: null,
      loading: true,
    }));
    api
      .innovations(
        {
          category: category || undefined,
          page,
          per_page: PER_PAGE,
          q: query.length >= 2 ? query : undefined,
        },
        abort.signal
      )
      .then((result) =>
        setList((current) => ({
          error: null,
          items:
            page === 1 ? result.items : [...current.items, ...result.items],
          loading: false,
          page: result.page,
          total: result.total,
        }))
      )
      .catch((caught: unknown) => {
        if (caught instanceof Error && caught.name === "AbortError") {
          return;
        }
        setList((current) => ({
          ...current,
          error: errorMessage(caught),
          loading: false,
        }));
      });
    return () => abort.abort();
  }, [category, query, page, attempt]);

  const selectCategory = (slug: string) => {
    setPage(1);
    router.setParams({ kategoria: slug === category ? "" : slug });
  };

  const search = () => {
    setPage(1);
    router.setParams({ q: draft.trim() });
  };

  const clearSearch = () => {
    setDraft("");
    setPage(1);
    router.setParams({ q: "" });
  };

  const activeCategory = categories.find((item) => item.slug === category);
  const summary = (() => {
    if (list.loading && list.items.length === 0) {
      return "Wczytuję…";
    }
    const count = `${list.total} ${pluralPl(
      list.total,
      "rozwiązanie",
      "rozwiązania",
      "rozwiązań"
    )}`;
    return [
      count,
      activeCategory ? activeCategory.name.toLowerCase() : null,
      query ? `dla „${query}”` : null,
    ]
      .filter(Boolean)
      .join(" ");
  })();

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
              <Button
                label="Spróbuj ponownie"
                onPress={() => setAttempt((value) => value + 1)}
              />
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
        {list.items.length > 0 && list.items.length < list.total ? (
          <Button
            busy={list.loading}
            label={list.loading ? "Wczytuję…" : "Pokaż więcej"}
            onPress={() => setPage((value) => value + 1)}
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
