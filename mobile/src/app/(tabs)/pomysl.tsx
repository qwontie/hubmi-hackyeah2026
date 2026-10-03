import { router } from "expo-router";
import Head from "expo-router/head";
import { PenLine, Search, X } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { CategoryFilter } from "@/features/category-filter";
import { CardGrid } from "@/features/innovation-card";
import { ProblemCard } from "@/features/problem-card";
import { useProblems } from "@/hooks/use-problems";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { AccessButton } from "@/ui/shell";
import { Heading, Txt } from "@/ui/text";

const ownIdea = () => router.push("/pomysl/nowy");

export default function ProblemsScreen() {
  const { wide } = useTheme();
  const {
    categories,
    category,
    clearSearch,
    draft,
    hasMore,
    list,
    loadMore,
    propose,
    query,
    retry,
    search,
    selectCategory,
    setDraft,
  } = useProblems();
  const empty = !(list.loading || list.error) && list.items.length === 0;

  return (
    <Screen tabs trailing={<AccessButton />} width={900}>
      <Head>
        <title>{`Problemy mieszkańców · ${APP_NAME}`}</title>
      </Head>
      <PageHead>
        <Heading level={1}>Problemy, które czekają na pomysł</Heading>
        <View style={[styles.search, wide && styles.searchWide]}>
          <View style={styles.flex}>
            <TextField
              enterKeyHint="search"
              hideLabel
              label="Szukaj problemu"
              onChangeText={setDraft}
              onSubmitEditing={search}
              placeholder="np. samotność seniorów"
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
          items={categories.map(({ slug, name }) => ({ name, slug }))}
          label="Kategorie"
          onSelect={selectCategory}
          value={category}
        />
        <View>
          <Button
            icon={PenLine}
            label="Mam własny pomysł"
            onPress={ownIdea}
            role="link"
            variant="quiet"
          />
        </View>
      </PageHead>

      <View aria-live="polite" style={styles.results}>
        {list.error ? (
          <Notice tone="error">
            <View style={styles.group}>
              <Txt>{list.error}</Txt>
              <Button label="Spróbuj ponownie" onPress={retry} />
            </View>
          </Notice>
        ) : null}
        {list.loading && list.items.length === 0 ? (
          <Txt tone="soft">Wczytuję problemy.</Txt>
        ) : null}
        {empty ? (
          <View style={styles.group}>
            <Txt>
              Tu pojawiają się problemy, które zgłosiły co najmniej 3 osoby. Na
              razie żaden nie pasuje do tego wyboru.
            </Txt>
            <Button
              icon={PenLine}
              label="Opisz własny pomysł"
              onPress={ownIdea}
              variant="primary"
            />
          </View>
        ) : null}
        {list.items.length > 0 ? (
          <>
            <Txt tone="soft" weight="500">
              {`${list.total} ${pluralPl(list.total, "problem", "problemy", "problemów")}`}
            </Txt>
            <CardGrid>
              {list.items.map((problem) => (
                <ProblemCard
                  key={problem.id}
                  onPropose={() => propose(problem.id)}
                  problem={problem}
                />
              ))}
            </CardGrid>
          </>
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
    marginHorizontal: -(space.lg + space.xs + 2),
  },
  buttons: {
    flexDirection: "row",
    gap: space.sm,
  },
  categories: {
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
  results: {
    gap: space.lg,
  },
  search: {
    gap: space.md,
  },
  searchWide: {
    alignItems: "center",
    flexDirection: "row",
  },
  strip: {
    gap: space.sm,
    paddingHorizontal: space.lg + space.xs + 2,
  },
  tall: {
    minHeight: 62,
  },
});
