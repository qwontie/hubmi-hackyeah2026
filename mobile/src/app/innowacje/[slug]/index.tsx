import { Image } from "expo-image";
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
import type { Ref } from "react";
import { StyleSheet, type Text, View } from "react-native";
import type { InnovationDetail } from "@/api/types";
import { API_BASE, APP_NAME } from "@/config";
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

const absolute = (url: string) =>
  url.startsWith("/") ? `${API_BASE}${url}` : url;

function Hero({
  data,
  titleRef,
}: {
  data: InnovationDetail;
  titleRef: Ref<Text>;
}) {
  const { colors, reduceMotion, wide } = useTheme();
  const picture = data.image_url
    ? {
        alt: data.image_alt ?? "",
        label: data.image_label ?? null,
        uri: absolute(data.image_url),
      }
    : null;
  const beside = wide && picture !== null;
  return (
    <View style={[styles.hero, beside && styles.heroWide]}>
      <View style={[styles.header, beside && styles.flex]}>
        {picture ? null : <CategoryTile size={64} slug={data.category.slug} />}
        <Heading level={1} ref={titleRef}>
          {data.title}
        </Heading>
        <Txt tone="soft" variant="lead">
          {data.lead}
        </Txt>
        <Txt tone="soft" variant="detail">
          {[innovationMeta(data), picture?.label]
            .filter(Boolean)
            .join(" · ")
            .replaceAll(" · ", "\u00a0· ")}
        </Txt>
      </View>
      {picture ? (
        <View
          style={[
            styles.picture,
            wide ? styles.pictureWide : styles.pictureNarrow,
            { backgroundColor: colors.paper },
          ]}
        >
          <Image
            accessibilityLabel={picture.alt}
            contentFit="cover"
            source={{ uri: picture.uri }}
            style={styles.image}
            transition={reduceMotion ? 0 : 240}
          />
        </View>
      ) : null}
    </View>
  );
}

export default function InnovationScreen() {
  const { slug, potrzeba } = useLocalSearchParams<{
    slug: string;
    potrzeba?: string;
  }>();
  const { colors, wide } = useTheme();
  const { state, retry, titleRef } = useInnovation(slug);

  const hero =
    state.kind === "done" ? (
      <Hero data={state.data} titleRef={titleRef} />
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
  flex: {
    flex: 1,
  },
  header: {
    gap: space.md,
  },
  hero: {
    gap: space.xl,
  },
  heroWide: {
    alignItems: "flex-start",
    flexDirection: "row",
  },
  image: {
    height: "100%",
    width: "100%",
  },
  links: {
    gap: space.md,
  },
  picture: {
    borderRadius: 20,
    overflow: "hidden",
  },
  pictureNarrow: {
    aspectRatio: 16 / 9,
  },
  pictureWide: {
    aspectRatio: 4 / 3,
    width: 300,
  },
  section: {
    gap: space.md,
  },
});
