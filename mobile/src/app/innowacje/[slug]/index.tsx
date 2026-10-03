import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import {
  BookOpen,
  Building2,
  Download,
  FileText,
  FlaskConical,
  Landmark,
} from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { CategoryTile } from "@/features/category-icon";
import { ReadAloudPill } from "@/features/read-aloud-button";
import { RichText } from "@/features/rich-text";
import { ImprovementBlock, VoteBlock } from "@/features/tester";
import { Video } from "@/features/video";
import {
  innovationMeta,
  innovationSections,
  innovationSpeech,
  useInnovation,
} from "@/hooks/use-innovation";
import { formatDate } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function InnovationScreen() {
  const { slug, potrzeba } = useLocalSearchParams<{
    slug: string;
    potrzeba?: string;
  }>();
  const { colors, wide } = useTheme();
  const { state, retry, titleRef } = useInnovation(slug);

  const hero =
    state.kind === "done" ? (
      <View style={styles.header}>
        <CategoryTile size={64} slug={state.data.category.slug} />
        <Heading level={1} ref={titleRef}>
          {state.data.title}
        </Heading>
        <Txt tone="soft" variant="lead">
          {state.data.lead}
        </Txt>
        <Txt tone="soft" variant="detail">
          {innovationMeta(state.data)}
        </Txt>
      </View>
    ) : undefined;

  return (
    <Screen
      back="Wróć"
      hero={hero}
      trailing={
        state.kind === "done" ? (
          <ReadAloudPill text={innovationSpeech(state.data)} />
        ) : undefined
      }
    >
      {state.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję opis rozwiązania.
        </Txt>
      ) : null}

      {state.kind === "error" ? (
        <Notice
          title={
            state.missing
              ? "Nie ma takiego rozwiązania"
              : "Nie udało się wczytać opisu"
          }
          tone="error"
        >
          <View style={styles.errorBody}>
            <Txt>
              {state.missing
                ? "Mogło zostać usunięte z biblioteki albo adres jest niepełny."
                : state.message}
            </Txt>
            {state.missing ? (
              <Button
                icon={BookOpen}
                label="Przejdź do biblioteki"
                onPress={() => router.replace("/biblioteka")}
              />
            ) : (
              <Button label="Spróbuj ponownie" onPress={retry} />
            )}
          </View>
        </Notice>
      ) : null}

      {state.kind === "done" ? (
        <>
          <Head>
            <title>{`${state.data.title} · ${APP_NAME}`}</title>
            <meta content={state.data.lead} name="description" />
          </Head>
          {state.data.video_url ? (
            <Sheet>
              <Heading level={2}>Film</Heading>
              <Video title={state.data.title} url={state.data.video_url} />
            </Sheet>
          ) : null}

          <Sheet>
            {innovationSections(state.data).map((section, index) => (
              <View
                key={section.title}
                style={[
                  styles.section,
                  index > 0 && {
                    borderTopColor: colors.rule,
                    borderTopWidth: 1,
                    paddingTop: wide ? space.xl : space.lg,
                  },
                ]}
              >
                <Heading level={2}>{section.title}</Heading>
                <RichText source={section.body} />
              </View>
            ))}
          </Sheet>

          <Sheet>
            <VoteBlock needId={potrzeba} slug={state.data.slug} />
          </Sheet>

          <Sheet>
            <Heading level={2}>Chcesz wprowadzić to u siebie?</Heading>
            <Txt>
              Opisz swoją gminę lub instytucję, a przygotujemy plan usługi
              opartej na tym rozwiązaniu.
            </Txt>
            <Button
              icon={Building2}
              label="Dostosuj dla mojej instytucji"
              onPress={() =>
                router.push({
                  params: { slug: state.data.slug },
                  pathname: "/innowacje/[slug]/dostosuj",
                })
              }
              variant="primary"
            />
          </Sheet>

          <Sheet>
            <View style={styles.header}>
              <Heading level={2}>Chcesz to przetestować?</Heading>
              <Button
                icon={FlaskConical}
                label="Zgłoś się do testów"
                onPress={() => router.push("/testy")}
                role="link"
              />
            </View>
            <View style={[styles.divider, { backgroundColor: colors.rule }]} />
            <ImprovementBlock slug={state.data.slug} />
          </Sheet>

          <Sheet>
            <Heading level={2}>Materiały i źródło</Heading>
            <View style={styles.links}>
              {state.data.materials_url ? (
                <ExternalLink
                  description="(plik do pobrania)"
                  href={state.data.materials_url}
                  icon={Download}
                  label="Pobierz materiały"
                />
              ) : null}
              {state.data.brochure_url ? (
                <ExternalLink
                  description="(PDF)"
                  href={state.data.brochure_url}
                  icon={FileText}
                  label="Folder z opisem"
                />
              ) : null}
              {state.data.terms_url ? (
                <ExternalLink
                  description="(PDF)"
                  href={state.data.terms_url}
                  icon={FileText}
                  label="Zasady korzystania z innowacji"
                />
              ) : null}
              <ExternalLink
                href={state.data.source_url}
                icon={Landmark}
                label="Zobacz na stronie ROPS w Krakowie"
              />
            </View>
            <Txt tone="soft" variant="detail">
              {[
                state.data.license ? `Licencja: ${state.data.license}` : null,
                `Aktualizacja: ${formatDate(state.data.updated_at)}`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </Txt>
          </Sheet>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  divider: {
    height: 1,
  },
  errorBody: {
    gap: space.md,
  },
  header: {
    gap: space.md,
  },
  links: {
    gap: space.md,
  },
  section: {
    gap: space.md,
  },
});
