import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import {
  ArrowLeft,
  BookOpen,
  Building2,
  Download,
  FileText,
  Landmark,
} from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, type Text, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { InnovationDetail } from "@/api/types";
import { APP_NAME } from "@/config";
import { ReadAloudButton } from "@/features/read-aloud-button";
import { plainText, RichText } from "@/features/rich-text";
import {
  ImprovementBlock,
  TestSignupBlock,
  VoteBlock,
} from "@/features/tester";
import { Video } from "@/features/video";
import { formatDate } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";
import { focusElement } from "@/ui/web-globals";

type State =
  | { kind: "loading" }
  | { kind: "done"; innovation: InnovationDetail }
  | { kind: "error"; message: string; missing: boolean };

const sectionsOf = (innovation: InnovationDetail) =>
  [
    { body: innovation.what_it_is, title: "Na czym polega rozwiązanie?" },
    { body: innovation.problems, title: "Jakich problemów dotyczy?" },
    { body: innovation.target_group, title: "Dla kogo jest to rozwiązanie?" },
    { body: innovation.who_can_use, title: "Kto może z niego skorzystać?" },
    { body: innovation.effectiveness ?? "", title: "Czy to działa?" },
  ].filter((section) => section.body.trim().length > 0);

const goBack = () => {
  if (router.canGoBack()) {
    router.back();
  } else {
    router.replace("/");
  }
};

export default function InnovationScreen() {
  const { slug, potrzeba } = useLocalSearchParams<{
    slug: string;
    potrzeba?: string;
  }>();
  const { colors, wide } = useTheme();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);
  const titleRef = useRef<Text>(null);

  useEffect(() => {
    if (!slug || attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setState({ kind: "loading" });
    api
      .innovation(slug, abort.signal)
      .then((innovation) => setState({ innovation, kind: "done" }))
      .catch((caught: unknown) => {
        if (caught instanceof Error && caught.name === "AbortError") {
          return;
        }
        setState({
          kind: "error",
          message: errorMessage(caught),
          missing: caught instanceof ApiError && caught.code === "not_found",
        });
      });
    return () => abort.abort();
  }, [slug, attempt]);

  useEffect(() => {
    if (state.kind === "done" && Platform.OS === "web") {
      focusElement(titleRef.current);
    }
  }, [state.kind]);

  return (
    <Screen>
      <View>
        <Button
          icon={ArrowLeft}
          label="Wróć"
          onPress={goBack}
          variant="quiet"
        />
      </View>

      {state.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję opis rozwiązania…
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
              <Button
                label="Spróbuj ponownie"
                onPress={() => setAttempt((value) => value + 1)}
              />
            )}
          </View>
        </Notice>
      ) : null}

      {state.kind === "done" ? (
        <>
          <Head>
            <title>{`${state.innovation.title} · ${APP_NAME}`}</title>
            <meta content={state.innovation.lead} name="description" />
          </Head>
          <Sheet raised>
            <View style={styles.header}>
              <Heading level={1} ref={titleRef}>
                {state.innovation.title}
              </Heading>
              <Txt tone="soft" variant="lead">
                {state.innovation.lead}
              </Txt>
              <Txt tone="soft" variant="detail">
                {[
                  state.innovation.category.name,
                  state.innovation.authors.length > 0
                    ? `Autorzy: ${state.innovation.authors.join(", ")}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </Txt>
            </View>
            <ReadAloudButton
              text={[
                state.innovation.title,
                state.innovation.lead,
                ...sectionsOf(state.innovation).map(
                  (section) => `${section.title} ${plainText(section.body)}`
                ),
              ].join(". ")}
            />
          </Sheet>

          {state.innovation.video_url ? (
            <Sheet>
              <Heading level={2}>Film</Heading>
              <Video
                title={state.innovation.title}
                url={state.innovation.video_url}
              />
            </Sheet>
          ) : null}

          <Sheet>
            {sectionsOf(state.innovation).map((section, index) => (
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
            <VoteBlock needId={potrzeba} slug={state.innovation.slug} />
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
                  params: { slug: state.innovation.slug },
                  pathname: "/innowacje/[slug]/dostosuj",
                })
              }
              variant="primary"
            />
          </Sheet>

          <Sheet>
            <TestSignupBlock slug={state.innovation.slug} />
            <View style={[styles.divider, { backgroundColor: colors.rule }]} />
            <ImprovementBlock slug={state.innovation.slug} />
          </Sheet>

          <Sheet>
            <Heading level={2}>Materiały i źródło</Heading>
            <View style={styles.links}>
              {state.innovation.materials_url ? (
                <ExternalLink
                  description="(plik do pobrania)"
                  href={state.innovation.materials_url}
                  icon={Download}
                  label="Pobierz materiały"
                />
              ) : null}
              {state.innovation.brochure_url ? (
                <ExternalLink
                  description="(PDF)"
                  href={state.innovation.brochure_url}
                  icon={FileText}
                  label="Folder z opisem"
                />
              ) : null}
              {state.innovation.terms_url ? (
                <ExternalLink
                  description="(PDF)"
                  href={state.innovation.terms_url}
                  icon={FileText}
                  label="Zasady korzystania z innowacji"
                />
              ) : null}
              <ExternalLink
                href={state.innovation.source_url}
                icon={Landmark}
                label="Zobacz na stronie ROPS w Krakowie"
              />
            </View>
            <Txt tone="soft" variant="detail">
              {[
                state.innovation.license
                  ? `Licencja: ${state.innovation.license}`
                  : null,
                `Aktualizacja: ${formatDate(state.innovation.updated_at)}`,
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
