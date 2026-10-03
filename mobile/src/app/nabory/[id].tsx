import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { useApplicationStart, useGrantCall } from "@/hooks/use-grants";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const date = (value: string) =>
  new Intl.DateTimeFormat("pl-PL", { dateStyle: "long" }).format(
    new Date(value)
  );

const phaseLabel = {
  closed: "Nabór zakończony",
  open: "Nabór otwarty",
  upcoming: "Nabór zapowiedziany",
} as const;

export default function GrantCallScreen() {
  const { id, pomysl } = useLocalSearchParams<{
    id: string;
    pomysl?: string;
  }>();
  const { state, retry } = useGrantCall(id);
  const start = useApplicationStart(id ?? "", pomysl);
  if (state.kind === "loading") {
    return (
      <Screen back="Nabory">
        <Txt aria-live="polite">Wczytuję nabór.</Txt>
      </Screen>
    );
  }
  if (state.kind === "error") {
    return (
      <Screen back="Nabory">
        <Notice title="Nie udało się wczytać naboru" tone="error">
          <View style={styles.group}>
            <Txt>{state.message}</Txt>
            <Button label="Spróbuj ponownie" onPress={retry} />
          </View>
        </Notice>
      </Screen>
    );
  }
  const call = state.data;
  return (
    <Screen back="Nabory" width={900}>
      <Head>
        <title>{`${call.title} · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        <Txt tone={call.phase === "open" ? "stamp" : "soft"} weight="600">
          {phaseLabel[call.phase]}
          {call.demo ? " · Nabór pokazowy" : ""}
        </Txt>
        <Heading level={1}>{call.title}</Heading>
        <Txt tone="soft">
          Od {date(call.opens_at)} do {date(call.closes_at)}
        </Txt>
        {call.description.split("\n\n").map((paragraph) => (
          <Txt key={paragraph}>{paragraph}</Txt>
        ))}
        {call.source_url ? (
          <ExternalLink href={call.source_url} label="Źródło naboru" />
        ) : null}
      </View>
      <Sheet>
        <View style={styles.group}>
          <Heading level={2}>Przygotuj wniosek na podstawie pomysłu</Heading>
          {call.phase === "open" ? null : (
            <Txt tone="soft">
              Wniosek można utworzyć tylko podczas otwartego naboru.
            </Txt>
          )}
          {call.phase === "open" && start.ideas.length === 0 ? (
            <Txt tone="soft">
              Najpierw opisz pomysł w zakładce Pomysł na tym urządzeniu.
            </Txt>
          ) : null}
          {call.phase === "open"
            ? start.ideas.map((idea) => (
                <Button
                  busy={start.busyId === idea.id}
                  disabled={start.busyId !== null}
                  key={idea.id}
                  label={`Przygotuj wniosek: ${idea.title}`}
                  onPress={() => start.start(idea)}
                />
              ))
            : null}
          {start.error ? <Notice tone="error">{start.error}</Notice> : null}
        </View>
      </Sheet>
      <View style={styles.group}>
        <Heading level={2}>Sekcje wniosku</Heading>
        {call.sections.map((section) => (
          <View key={section.key}>
            <Txt weight="600">
              {section.label}
              {section.required ? " (wymagane)" : ""}
            </Txt>
            {section.hint ? <Txt tone="soft">{section.hint}</Txt> : null}
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({ group: { gap: space.md } });
