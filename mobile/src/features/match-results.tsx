import { Link } from "expo-router";
import { ArrowRight, CircleAlert } from "lucide-react-native";
import { type Ref, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  type Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { MatchResponse } from "@/api/types";
import { A11yButton } from "@/features/a11y-controls";
import { ContactForm } from "@/features/contact-form";
import { CardGrid, InnovationCard } from "@/features/innovation-card";
import { ReadAloudPill } from "@/features/read-aloud-button";
import { Stamp } from "@/features/stamp";
import { matchSpeech, resultsTitle, similarSentence } from "@/hooks/use-match";
import { useTheme } from "@/theme/settings";
import { minTarget, motion, radius, space, tabBarSpace } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { nightAttr } from "@/ui/night";
import { Notice } from "@/ui/notice";
import { Rise } from "@/ui/rise";
import { BackPill, WIDE_TOP } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

type SearchNeed = NonNullable<MatchResponse["need"]>;

export interface Registration {
  busy: boolean;
  error: string | null;
  need: { at: Date; number: number | null } | null;
  onRegister: () => void;
}

function Unsolved({ registration }: { registration: Registration }) {
  const { colors, wide } = useTheme();
  const { busy, error, need, onRegister } = registration;
  return (
    <View
      aria-live="polite"
      style={[styles.unsolved, { backgroundColor: colors.night }]}
      {...nightAttr(true)}
    >
      {need ? (
        <View style={[styles.unsolvedDone, wide && styles.unsolvedDoneWide]}>
          <Stamp at={need.at} number={need.number} word="PRZYJĘTO" />
          <View style={styles.unsolvedText}>
            <Heading level={3} night>
              ROPS przyjął Twoje zgłoszenie
            </Heading>
            <Txt tone="onNightSoft">
              Pracownik urzędu przeczyta opis. Odpowiedź znajdziesz w zakładce
              Zgłoszenia, tam też możesz podać e-mail.
            </Txt>
            <Link asChild href="/zgloszenia">
              <Pressable role="link" style={styles.unsolvedLink}>
                <Txt tone="onNight" variant="label" weight="600">
                  Przejdź do zgłoszeń
                </Txt>
                <ArrowRight aria-hidden color={colors.onNight} size={22} />
              </Pressable>
            </Link>
          </View>
        </View>
      ) : (
        <>
          <View style={styles.unsolvedText}>
            <Heading level={3} night size="h2">
              Żadne z tych rozwiązań nie pomaga?
            </Heading>
            <Txt tone="onNightSoft" variant="lead">
              Przekaż swój problem do ROPS. Pracownik urzędu przeczyta go i
              odpowie.
            </Txt>
          </View>
          {error ? (
            <View style={styles.unsolvedError}>
              <CircleAlert aria-hidden color={colors.onNight} size={24} />
              <Txt style={styles.metaText} tone="onNight" weight="600">
                {error}
              </Txt>
            </View>
          ) : null}
          <Button
            busy={busy}
            fill={!wide}
            label="Mój problem nie został rozwiązany"
            onPress={onRegister}
            size="large"
            variant="light"
          />
        </>
      )}
    </View>
  );
}

function NothingFits({ need, empty }: { need: SearchNeed; empty: boolean }) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(empty);
  const [done, setDone] = useState<{ email: string | null } | null>(null);

  if (done) {
    return (
      <Notice title="Przekazaliśmy to do ROPS" tone="success">
        <Txt>
          {done.email
            ? `Pracownik ROPS przeczyta opis i odpisze na adres ${done.email}.`
            : "Pracownik ROPS przeczyta Twój opis. Jeśli chcesz dostać odpowiedź, dodaj e-mail w zakładce Zgłoszenia."}
        </Txt>
        <Link href="/zgloszenia" style={{ color: colors.stamp }}>
          <Txt tone="stamp" weight="600">
            Przejdź do zgłoszeń
          </Txt>
        </Link>
      </Notice>
    );
  }

  return (
    <Sheet>
      <View style={styles.nothing}>
        <Heading level={3}>
          {empty ? "Przekaż problem do ROPS" : "Nic z tego nie pasuje?"}
        </Heading>
        <Txt tone="soft">
          Daj znać pracownikom ROPS. Zostaw e-mail, jeśli chcesz, żeby ktoś
          odpisał.
        </Txt>
      </View>
      {open ? (
        <ContactForm
          needId={need.id}
          nothingFits
          onDone={(email) => setDone({ email })}
          submitLabel="Wyślij do ROPS"
          token={need.edit_token}
        />
      ) : (
        <Button label="Nic nie pasuje" onPress={() => setOpen(true)} />
      )}
    </Sheet>
  );
}

interface MatchResultsProps {
  at: Date;
  onReset: () => void;
  registration: Registration;
  response: MatchResponse;
  settle: number;
  text: string;
  titleRef: Ref<Text>;
}

export function MatchResults({
  response,
  at,
  titleRef,
  text,
  onReset,
  settle,
  registration,
}: MatchResultsProps) {
  const searchNeed = response.need as SearchNeed | null | undefined;
  const { colors, type, wide, roomy } = useTheme();
  const insets = useSafeAreaInsets();
  const count = response.results.length;
  const empty = count === 0;
  const [first, ...rest] = response.results;
  const similar =
    response.similar_count > 0
      ? `${response.similar_count} ${similarSentence(response.similar_count)}`
      : similarSentence(0);
  const quoteSize = wide ? type.h2 : Math.round(type.h3 * 1.1);

  const band = (
    <View
      style={[
        styles.band,
        { backgroundColor: colors.night },
        wide
          ? styles.bandWide
          : { paddingTop: insets.top + space.sm, zIndex: 2 },
        roomy && styles.bandRoomy,
      ]}
      {...nightAttr(true)}
    >
      <View style={[styles.bandBar, wide && styles.bandBarWide]}>
        <BackPill label="Nowe pytanie" night onPress={onReset} />
        {wide && !empty ? (
          <ReadAloudPill night text={matchSpeech(response)} />
        ) : null}
        <A11yButton night />
      </View>
      <Txt
        style={{
          fontSize: quoteSize,
          letterSpacing: quoteSize * -0.02,
          lineHeight: Math.round(quoteSize * 1.28),
        }}
        tone="onNight"
        weight="500"
      >
        {text}
      </Txt>
      <Txt tone="onNightSoft" variant="label">
        {similar}
      </Txt>
      {searchNeed ? (
        <View style={wide ? styles.stampWide : styles.stamp}>
          <Stamp
            at={at}
            delay={settle + 200}
            number={searchNeed.number}
            word="PRZYJĘTO"
          />
        </View>
      ) : null}
    </View>
  );

  const list = (
    <View
      style={[
        styles.body,
        wide ? styles.bodyWide : styles.bodyNarrow,
        roomy && styles.bodyRoomy,
      ]}
    >
      <Heading
        level={2}
        nativeID="results-title"
        ref={titleRef}
        size={wide ? "h1" : "h2"}
      >
        {resultsTitle(count)}
      </Heading>

      {response.degraded ? (
        <Txt tone="soft" variant="detail">
          Asystent jest teraz przeciążony, więc opisy dopasowania są
          uproszczone. Same propozycje pochodzą z biblioteki ROPS.
        </Txt>
      ) : null}

      {first ? (
        <Rise delay={settle + 60}>
          <InnovationCard
            featured
            index={1}
            innovation={first.innovation}
            needId={searchNeed?.id}
            reason={first.reason}
          />
        </Rise>
      ) : null}

      {rest.length > 0 ? (
        <Rise delay={settle + 60 + motion.stagger * 2}>
          <CardGrid>
            {rest.map((result, index) => (
              <InnovationCard
                index={index + 2}
                innovation={result.innovation}
                key={result.innovation.slug}
                needId={searchNeed?.id}
                reason={result.reason}
              />
            ))}
          </CardGrid>
        </Rise>
      ) : null}

      {searchNeed ? (
        <NothingFits empty={empty} need={searchNeed} />
      ) : (
        <Unsolved registration={registration} />
      )}
    </View>
  );

  if (wide) {
    return (
      <View
        role="main"
        style={[styles.split, { backgroundColor: colors.ground }]}
      >
        {band}
        <ScrollView
          contentContainerStyle={styles.scrollWide}
          keyboardShouldPersistTaps="handled"
          style={styles.fill}
        >
          {list}
        </ScrollView>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={{
        paddingBottom: tabBarSpace + insets.bottom,
      }}
      keyboardShouldPersistTaps="handled"
      style={[styles.fill, { backgroundColor: colors.ground }]}
    >
      <View role="main">
        {band}
        {list}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  band: {
    borderBottomLeftRadius: radius.band,
    borderBottomRightRadius: radius.band,
    gap: space.lg,
    paddingBottom: 58,
    paddingHorizontal: space.xl - 2,
  },
  bandBar: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
    justifyContent: "space-between",
    marginBottom: space.sm,
  },
  bandBarWide: {
    marginBottom: space.xxl,
  },
  bandRoomy: {
    width: 560,
  },
  bandWide: {
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 44,
    borderTopRightRadius: 44,
    gap: space.xl,
    paddingBottom: 190,
    paddingHorizontal: 40,
    paddingTop: WIDE_TOP,
    width: 440,
    zIndex: 2,
  },
  best: {
    gap: space.md,
  },
  body: {
    gap: space.lg,
    width: "100%",
  },
  bodyNarrow: {
    paddingHorizontal: space.lg,
    paddingTop: 64,
  },
  bodyRoomy: {
    maxWidth: 1180,
  },
  bodyWide: {
    alignSelf: "center",
    maxWidth: 860,
    paddingHorizontal: 56,
  },
  cta: {
    alignItems: "center",
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.sm,
    justifyContent: "center",
    marginTop: space.sm,
    minHeight: 58,
    paddingHorizontal: space.xl,
  },
  ctaWide: {
    alignSelf: "flex-start",
    minWidth: 300,
  },
  fill: {
    flex: 1,
  },
  meta: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
  },
  metaText: {
    flex: 1,
  },
  nothing: {
    gap: space.sm,
  },
  pill: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
    paddingHorizontal: space.lg + 2,
  },
  pillPress: {
    borderRadius: radius.pill,
  },
  rows: {
    paddingHorizontal: space.xs,
  },
  scrollWide: {
    paddingBottom: space.xxxl * 2,
    paddingTop: WIDE_TOP + 20,
  },
  split: {
    flex: 1,
    flexDirection: "row",
  },
  stamp: {
    bottom: -38,
    position: "absolute",
    right: space.xl - 2,
  },
  stampWide: {
    bottom: 64,
    position: "absolute",
    right: -64,
  },
  unsolved: {
    borderRadius: radius.sheet,
    gap: space.xl,
    padding: space.xl,
  },
  unsolvedDone: {
    gap: space.xl,
  },
  unsolvedDoneWide: {
    alignItems: "center",
    flexDirection: "row",
  },
  unsolvedError: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.sm + 2,
  },
  unsolvedLink: {
    alignItems: "center",
    alignSelf: "flex-start",
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
  },
  unsolvedText: {
    flex: 1,
    gap: space.sm + 2,
  },
});
