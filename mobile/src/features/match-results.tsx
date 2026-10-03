import { Link } from "expo-router";
import { ArrowRight } from "lucide-react-native";
import { type Ref, useState } from "react";
import {
  Pressable,
  ScrollView,
  StyleSheet,
  type Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import type { MatchResponse, MatchResult } from "@/api/types";
import { CategoryIcon } from "@/features/category-icon";
import { ContactForm } from "@/features/contact-form";
import {
  InnovationRow,
  innovationHref,
  metaLine,
} from "@/features/innovation-row";
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

function NothingFits({
  response,
  empty,
}: {
  response: MatchResponse;
  empty: boolean;
}) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(empty);
  const [done, setDone] = useState<{ email: string | null } | null>(null);

  if (done) {
    return (
      <Notice title="Przekazaliśmy to do ROPS" tone="success">
        <Txt>
          {done.email
            ? `Pracownik ROPS przeczyta Twój opis i odpisze na adres ${done.email}.`
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
          needId={response.need.id}
          nothingFits
          onDone={(email) => setDone({ email })}
          submitLabel="Wyślij do ROPS"
          token={response.need.edit_token}
        />
      ) : (
        <Button label="Nic nie pasuje" onPress={() => setOpen(true)} />
      )}
    </Sheet>
  );
}

function BestMatch({
  result,
  needId,
}: {
  result: MatchResult;
  needId: string;
}) {
  const { colors, type, wide, reduceMotion } = useTheme();
  const [hovered, setHovered] = useState(false);
  const { innovation } = result;
  return (
    <Link asChild href={innovationHref(innovation.slug, needId)}>
      <Pressable
        onHoverIn={() => setHovered(true)}
        onHoverOut={() => setHovered(false)}
        role="link"
        style={{
          transform: [{ translateY: hovered && !reduceMotion ? -3 : 0 }],
        }}
      >
        <Sheet raised style={styles.best}>
          <Txt
            style={{
              fontSize: wide ? type.h1 : type.h2,
              letterSpacing: (wide ? type.h1 : type.h2) * -0.032,
              lineHeight: Math.round((wide ? type.h1 : type.h2) * 1.08),
            }}
            weight="600"
          >
            {innovation.title}
          </Txt>
          <Txt tone="soft" variant="lead">
            {result.reason}
          </Txt>
          <View style={styles.meta}>
            <CategoryIcon
              color={colors.inkSoft}
              size={18}
              slug={innovation.category.slug}
            />
            <Txt style={styles.metaText} tone="soft" variant="small">
              {metaLine(innovation)}
            </Txt>
          </View>
          <View
            style={[
              styles.cta,
              {
                backgroundColor: hovered ? colors.stampPress : colors.stamp,
              },
              wide && styles.ctaWide,
            ]}
          >
            <Txt tone="onStamp" variant="lead" weight="600">
              Zobacz rozwiązanie
            </Txt>
            <ArrowRight aria-hidden color={colors.onStamp} size={22} />
          </View>
        </Sheet>
      </Pressable>
    </Link>
  );
}

interface MatchResultsProps {
  at: Date;
  onReset: () => void;
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
}: MatchResultsProps) {
  const { colors, type, wide } = useTheme();
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
      ]}
      {...nightAttr(true)}
    >
      <View style={[styles.bandBar, wide && styles.bandBarWide]}>
        <BackPill label="Nowe pytanie" night onPress={onReset} />
        {empty ? null : <ReadAloudPill night text={matchSpeech(response)} />}
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
      <View style={wide ? styles.stampWide : styles.stamp}>
        <Stamp
          at={at}
          delay={settle + 200}
          number={response.need.number}
          word="PRZYJĘTO"
        />
      </View>
    </View>
  );

  const list = (
    <View
      role="main"
      style={[styles.body, wide ? styles.bodyWide : styles.bodyNarrow]}
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
          <BestMatch needId={response.need.id} result={first} />
        </Rise>
      ) : null}

      {rest.length > 0 ? (
        <View role="list" style={styles.rows}>
          {rest.map((result, index) => (
            <Rise
              delay={settle + 160 + index * motion.stagger}
              key={result.innovation.slug}
            >
              <InnovationRow
                index={index + 2}
                innovation={result.innovation}
                last={index === rest.length - 1}
                needId={response.need.id}
                reason={result.reason}
              />
            </Rise>
          ))}
        </View>
      ) : null}

      <NothingFits empty={empty} response={response} />
    </View>
  );

  if (wide) {
    return (
      <View style={[styles.split, { backgroundColor: colors.ground }]}>
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
      {band}
      {list}
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
    justifyContent: "space-between",
    marginBottom: space.sm,
  },
  bandBarWide: {
    marginBottom: space.xxl,
  },
  bandWide: {
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 44,
    borderTopRightRadius: 44,
    gap: space.xl,
    paddingBottom: 40,
    paddingHorizontal: 40,
    paddingTop: WIDE_TOP,
    width: 440,
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
    marginTop: "auto",
  },
});
