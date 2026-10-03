import { Link } from "expo-router";
import type { Ref } from "react";
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
import { CrisisHelp } from "@/features/crisis-help";
import { DemoTag } from "@/features/demo-tag";
import { CardGrid, InnovationCard } from "@/features/innovation-card";
import { ReadAloudPill } from "@/features/read-aloud-button";
import { RopsFooter } from "@/features/rops-footer";
import { type Registration, Unsolved } from "@/features/unsolved";
import {
  matchSpeech,
  PROBLEM_PAGE_MIN,
  resultsTitle,
  similarCount,
  similarSentence,
} from "@/hooks/use-match";
import { isCrisis } from "@/lib/crisis";
import { useTheme } from "@/theme/settings";
import { minTarget, motion, radius, space, tabBarSpace } from "@/theme/tokens";
import { nightAttr } from "@/ui/night";
import { Rise } from "@/ui/rise";
import { BackPill, WIDE_TOP } from "@/ui/screen";
import { Heading, Txt } from "@/ui/text";

const AI_NOTE =
  "Rozwiązania pochodzą z biblioteki ROPS. Zdania o tym, dlaczego pasują, napisała sztuczna inteligencja.";

function Similar({ response }: { response: MatchResponse }) {
  const group = response.cluster;
  const similar = similarCount(response);
  if (similar === 0) {
    return null;
  }
  return (
    <View style={styles.similar}>
      <Txt tone="onNightSoft" variant="label">
        {`${similar} ${similarSentence(similar)}`}
      </Txt>
      {group && group.size >= PROBLEM_PAGE_MIN ? (
        <Link
          asChild
          href={{ params: { id: group.id }, pathname: "/problemy/[id]" }}
        >
          <Pressable role="link" style={styles.groupLink}>
            <Txt
              style={styles.groupTitle}
              tone="onNight"
              variant="label"
              weight="600"
            >
              {`Zobacz ten problem: ${group.title}`}
            </Txt>
          </Pressable>
        </Link>
      ) : null}
      <DemoTag night />
    </View>
  );
}

interface MatchResultsProps {
  onEdit: () => void;
  onReset: () => void;
  registration: Registration;
  response: MatchResponse;
  settle: number;
  text: string;
  titleRef: Ref<Text>;
}

export function MatchResults({
  response,
  titleRef,
  text,
  onEdit,
  onReset,
  settle,
  registration,
}: MatchResultsProps) {
  const { colors, type, wide, roomy } = useTheme();
  const insets = useSafeAreaInsets();
  const count = response.results.length;
  const empty = count === 0;
  const [first, ...rest] = response.results;
  const crisis = isCrisis(text);
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
      <Similar response={response} />
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
        level={1}
        nativeID="results-title"
        ref={titleRef}
        size={wide ? "h1" : "h2"}
      >
        {resultsTitle(count)}
      </Heading>

      {empty ? (
        <Txt tone="soft" variant="lead">
          Problem jest opisany niejasno albo jeszcze go nie rozwiązaliśmy.
        </Txt>
      ) : null}

      {crisis ? <CrisisHelp /> : null}

      {response.degraded ? (
        <Txt tone="soft" variant="detail">
          Asystent jest teraz przeciążony, więc opisy dopasowania są
          uproszczone. Same propozycje pochodzą z biblioteki ROPS.
        </Txt>
      ) : null}

      {empty || response.degraded ? null : (
        <Txt tone="soft" variant="detail">
          {AI_NOTE}
        </Txt>
      )}

      {first ? (
        <Rise delay={settle + 60}>
          <InnovationCard
            featured
            index={1}
            innovation={first.innovation}
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
                reason={result.reason}
              />
            ))}
          </CardGrid>
        </Rise>
      ) : null}

      <Unsolved empty={empty} onEdit={onEdit} registration={registration} />
      <RopsFooter />
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
  groupLink: {
    alignSelf: "flex-start",
    justifyContent: "center",
    minHeight: minTarget,
  },
  groupTitle: {
    flexShrink: 1,
    textDecorationLine: "underline",
  },
  meta: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
  },
  metaText: {
    flex: 1,
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
  similar: {
    gap: space.xs,
  },
  split: {
    flex: 1,
    flexDirection: "row",
  },
});
