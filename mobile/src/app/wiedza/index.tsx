import { router } from "expo-router";
import Head from "expo-router/head";
import { FileText, Search, X } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { CategoryFilter } from "@/features/category-filter";
import { ChallengeRow } from "@/features/knowledge";
import { useChallenges } from "@/hooks/use-knowledge";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Txt } from "@/ui/text";

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
    <Screen
      back="Biblioteka"
      backFallback="/biblioteka"
      title="Wyzwania społeczne Małopolski"
      width={900}
    >
      <Head>
        <title>{`Wyzwania Małopolski · ${APP_NAME}`}</title>
      </Head>
      <PageHead>
        <View style={[styles.group, wide && styles.searchWide]}>
          <View style={styles.flex}>
            <TextField
              enterKeyHint="search"
              hideLabel
              label="Szukaj wyzwania"
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
          items={areas}
          label="Obszary"
          onSelect={selectArea}
          value={area}
        />
        <Button
          icon={FileText}
          label="Raporty i materiały ROPS"
          onPress={() => router.push("/materialy")}
          variant="quiet"
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
    alignItems: "stretch",
    flexDirection: "row",
  },
  tall: {
    alignSelf: "stretch",
    minHeight: 62,
  },
});
