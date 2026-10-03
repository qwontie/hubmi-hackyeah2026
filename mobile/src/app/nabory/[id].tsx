import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { FileText, Pencil } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { GrantCall, GrantSection } from "@/api/types";
import { APP_NAME } from "@/config";
import { useApplicationStart, useGrantCall } from "@/hooks/use-grants";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const NBSP = "\u00a0";

const date = (value: string) =>
  new Intl.DateTimeFormat("pl-PL", { dateStyle: "long" })
    .format(new Date(value))
    .replaceAll(" ", NBSP);

const dateRange = (from: string, to: string) => {
  const start = new Date(from);
  const end = new Date(to);
  const sameMonth =
    start.getFullYear() === end.getFullYear() &&
    start.getMonth() === end.getMonth();
  return sameMonth
    ? `Od ${start.getDate()} do${NBSP}${date(to)}`
    : `Od ${date(from)} do${NBSP}${date(to)}`;
};

const phaseLabel = {
  closed: "Nabór zakończony",
  open: "Nabór otwarty",
  upcoming: "Nabór zapowiedziany",
} as const;

function Start({ call, ideaId }: { call: GrantCall; ideaId?: string }) {
  const start = useApplicationStart(call.id, ideaId);
  const open = call.phase === "open";
  return (
    <Sheet raised={open}>
      <View style={styles.group}>
        <Heading level={2}>Przygotuj wniosek na podstawie pomysłu</Heading>
        {open ? (
          <Txt tone="soft">
            Sztuczna inteligencja ułoży szkic odpowiedzi z Twojego pomysłu.
            Potem przeczytasz go i poprawisz.
          </Txt>
        ) : (
          <Txt tone="soft">
            Wniosek można utworzyć tylko podczas otwartego naboru.
          </Txt>
        )}
        {open && start.ideas.length === 0 ? (
          <View style={styles.group}>
            <Txt>Na tym urządzeniu nie ma jeszcze zapisanego pomysłu.</Txt>
            <View style={styles.actions}>
              <Button
                icon={Pencil}
                label="Opisz pomysł"
                onPress={() => router.push("/pomysl/nowy")}
                variant="primary"
              />
            </View>
          </View>
        ) : null}
        {open ? (
          <View style={styles.actions}>
            {start.ideas.map((idea) => (
              <Button
                busy={start.busyId === idea.id}
                disabled={start.busyId !== null}
                icon={FileText}
                key={idea.id}
                label={`Przygotuj wniosek: ${idea.title}`}
                onPress={() => start.start(idea)}
                variant="primary"
              />
            ))}
          </View>
        ) : null}
        {start.error ? <Notice tone="error">{start.error}</Notice> : null}
      </View>
    </Sheet>
  );
}

function Questions({ sections }: { sections: GrantSection[] }) {
  const { colors } = useTheme();
  const allRequired = sections.every((section) => section.required);
  return (
    <Sheet>
      <View style={styles.group}>
        <Heading level={2}>Pytania we wniosku</Heading>
        <Txt tone="soft">
          {`${sections.length} ${pluralPl(sections.length, "pytanie", "pytania", "pytań")}.`}
          {allRequired ? " Odpowiedź na każde jest wymagana." : ""}
        </Txt>
      </View>
      <View role="list">
        {sections.map((section, index) => (
          <View
            key={section.key}
            role="listitem"
            style={[
              styles.question,
              { borderTopColor: colors.rule },
              index === 0 && styles.first,
            ]}
          >
            <Txt mono style={styles.number} tone="stamp" weight="600">
              {String(index + 1).padStart(2, "0")}
            </Txt>
            <View style={styles.questionText}>
              <Txt weight="600">
                {section.label}
                {allRequired || section.required ? "" : " (nieobowiązkowe)"}
              </Txt>
              {section.hint ? (
                <Txt tone="soft" variant="detail">
                  {section.hint}
                </Txt>
              ) : null}
            </View>
          </View>
        ))}
      </View>
    </Sheet>
  );
}

export default function GrantCallScreen() {
  const { id, pomysl } = useLocalSearchParams<{
    id: string;
    pomysl?: string;
  }>();
  const { state, retry } = useGrantCall(id);
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
  const hero = (
    <View style={styles.group}>
      <Txt
        tone={call.phase === "open" ? "stamp" : "soft"}
        variant="detail"
        weight="600"
      >
        {phaseLabel[call.phase]}
        {call.demo ? " · Nabór pokazowy" : ""}
      </Txt>
      <Heading level={1}>{call.title}</Heading>
      <Txt tone="soft" variant="lead">
        {dateRange(call.opens_at, call.closes_at)}
      </Txt>
    </View>
  );
  return (
    <Screen back="Nabory" backFallback="/nabory" hero={hero} width={900}>
      <Head>
        <title>{`${call.title} · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        {call.description.split("\n\n").map((paragraph) => (
          <Txt key={paragraph}>{paragraph}</Txt>
        ))}
        {call.source_url ? (
          <View style={styles.actions}>
            <ExternalLink href={call.source_url} label="Źródło naboru" />
          </View>
        ) : null}
      </View>
      <Start call={call} ideaId={pomysl} />
      <Questions sections={call.sections} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: "flex-start", gap: space.sm },
  first: { borderTopWidth: 0 },
  group: { gap: space.md },
  number: { minWidth: 32 },
  question: {
    borderTopWidth: 1,
    flexDirection: "row",
    gap: space.md,
    paddingVertical: space.md,
  },
  questionText: { flex: 1, gap: space.xs },
});
