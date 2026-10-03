import Head from "expo-router/head";
import { Check, Clock, MapPin } from "lucide-react-native";
import { useEffect, useRef } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import type { MapPowiat } from "@/api/types";
import { APP_NAME } from "@/config";
import { type MapCount, ProblemMap } from "@/features/problem-map";
import { MAP_ATTRIBUTION, useMap } from "@/hooks/use-map";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const openWords = (count: number) =>
  `${count} ${pluralPl(count, "potrzeba czeka", "potrzeby czekają", "potrzeb czeka")} na odpowiedź`;

const answeredWords = (count: number) =>
  `${count} ${pluralPl(count, "potrzeba", "potrzeby", "potrzeb")} z odpowiedzią ROPS`;

const countOf = (powiat: MapPowiat): MapCount => ({
  answered: powiat.needs_answered ?? 0,
  open: powiat.needs_open ?? 0,
});

function Tally({ count }: { count: MapCount }) {
  const { colors } = useTheme();
  if (count.open + count.answered === 0) {
    return <Txt tone="soft">Nikt jeszcze nie zgłosił tu potrzeby.</Txt>;
  }
  return (
    <View style={styles.tally}>
      <View style={styles.tallyLine}>
        <Clock aria-hidden color={colors.stamp} size={22} />
        <Txt style={styles.grow} weight="500">
          {openWords(count.open)}
        </Txt>
      </View>
      <View style={styles.tallyLine}>
        <Check aria-hidden color={colors.ok} size={22} strokeWidth={2.6} />
        <Txt style={styles.grow} weight="500">
          {answeredWords(count.answered)}
        </Txt>
      </View>
    </View>
  );
}

function PowiatPanel({
  powiat,
  onReport,
}: {
  powiat: MapPowiat;
  onReport: () => void;
}) {
  const { colors } = useTheme();
  const problems = powiat.problems ?? [];
  const otherOpen = powiat.other_open ?? 0;
  const otherAnswered = powiat.other_answered ?? 0;
  return (
    <Sheet aria-live="polite" raised>
      <View style={styles.group}>
        <Heading level={2}>{powiat.name}</Heading>
        <Tally count={countOf(powiat)} />
      </View>

      {problems.length > 0 ? (
        <View style={styles.group}>
          <Heading level={3}>Najczęstsze problemy</Heading>
          <View role="list">
            {problems.map((problem, index) => (
              <View
                key={problem.title}
                role="listitem"
                style={[
                  styles.problem,
                  index > 0 && {
                    borderTopColor: colors.rule,
                    borderTopWidth: 1,
                  },
                ]}
              >
                <Txt weight="600">{problem.title}</Txt>
                <Txt tone="soft" variant="label">
                  {`${openWords(problem.open)}, ${answeredWords(problem.answered)}`}
                </Txt>
              </View>
            ))}
          </View>
          {otherOpen + otherAnswered > 0 ? (
            <Txt tone="soft" variant="label">
              {`Inne zgłoszenia: ${otherOpen + otherAnswered}.`}
            </Txt>
          ) : null}
        </View>
      ) : null}

      <Button
        icon={MapPin}
        label="Zgłoś problem w tym powiecie"
        onPress={onReport}
        size="large"
        variant="primary"
      />
    </Sheet>
  );
}

export default function MapScreen() {
  const { colors, wide, highContrast } = useTheme();
  const { data, load, projection, report, retry, select, selected } = useMap();
  const opened = useRef(false);

  useEffect(() => {
    if (!data || opened.current) {
      return;
    }
    opened.current = true;
    const needsOf = (powiat: MapPowiat) =>
      (powiat.needs_open ?? 0) + (powiat.needs_answered ?? 0);
    const [busiest] = [...data.powiats].sort((a, b) => needsOf(b) - needsOf(a));
    if (busiest && needsOf(busiest) > 0) {
      select(busiest.slug);
    }
  }, [data, select]);
  const counts: Record<string, MapCount> = Object.fromEntries(
    (data?.powiats ?? []).map((powiat) => [powiat.slug, countOf(powiat)])
  );
  const total = Object.values(counts).reduce(
    (sum, count) => ({
      answered: sum.answered + count.answered,
      open: sum.open + count.open,
    }),
    { answered: 0, open: 0 }
  );

  const map =
    projection && data ? (
      <View style={styles.group}>
        <ProblemMap
          counts={counts}
          height={projection.height}
          onSelect={select}
          selected={selected?.slug ?? null}
          shapes={projection.shapes}
          width={projection.width}
        />
        <Txt tone="soft" variant="small">
          {`Wybierz powiat na mapie albo z listy. Ciemniejszy to więcej zgłoszeń. ${MAP_ATTRIBUTION}.`}
        </Txt>
      </View>
    ) : null;

  const list = data ? (
    <View style={styles.group}>
      <Heading level={2}>Powiaty</Heading>
      <View role="list">
        {data.powiats.map((powiat, index) => {
          const count = countOf(powiat);
          const active = selected?.slug === powiat.slug;
          return (
            <View
              key={powiat.slug}
              role="listitem"
              style={
                index > 0 && {
                  borderTopColor: highContrast ? colors.ink : colors.rule,
                  borderTopWidth: 1,
                }
              }
            >
              <Pressable
                aria-pressed={active}
                onPress={() => select(active ? null : powiat.slug)}
                role="button"
                style={styles.row}
              >
                <Txt
                  style={styles.grow}
                  tone={active ? "stamp" : "default"}
                  weight={active ? "600" : "500"}
                >
                  {powiat.name}
                </Txt>
                <Txt tone="soft" variant="label">
                  {count.open + count.answered > 0
                    ? `${count.open} czeka · ${count.answered} z odpowiedzią`
                    : "brak zgłoszeń"}
                </Txt>
              </Pressable>
            </View>
          );
        })}
      </View>
    </View>
  ) : null;

  return (
    <Screen tabs width={wide ? 1180 : undefined}>
      <Head>
        <title>{`Mapa potrzeb · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        <Heading level={1}>Mapa potrzeb</Heading>
        {data ? (
          <Txt tone="soft" variant="lead">
            {total.open + total.answered > 0
              ? `Mieszkańcy Małopolski zgłosili ${total.open + total.answered} ${pluralPl(total.open + total.answered, "potrzebę", "potrzeby", "potrzeb")}: ${total.open} czeka na odpowiedź, ${total.answered} ma odpowiedź ROPS.`
              : "Tu pojawią się potrzeby zgłoszone przez mieszkańców Małopolski."}
          </Txt>
        ) : null}
      </View>

      {load.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję mapę.
        </Txt>
      ) : null}

      {load.kind === "error" ? (
        <Notice title="Nie udało się wczytać mapy" tone="error">
          <View style={styles.group}>
            <Txt>{load.message}</Txt>
            <Button label="Spróbuj ponownie" onPress={retry} />
          </View>
        </Notice>
      ) : null}

      {wide ? (
        <View style={styles.split}>
          <View style={styles.mapWide}>{map}</View>
          <View style={styles.side}>
            {selected ? (
              <PowiatPanel
                onReport={() => report(selected.slug)}
                powiat={selected}
              />
            ) : null}
            {list ? <Sheet>{list}</Sheet> : null}
          </View>
        </View>
      ) : (
        <>
          {map}
          {selected ? (
            <PowiatPanel
              onReport={() => report(selected.slug)}
              powiat={selected}
            />
          ) : null}
          {list ? <Sheet>{list}</Sheet> : null}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  figure: {
    gap: space.xs,
  },
  group: {
    gap: space.md,
  },
  grow: {
    flex: 1,
  },
  mapWide: {
    flex: 1.15,
  },
  problem: {
    gap: space.xs,
    paddingVertical: space.md,
  },
  row: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget + 8,
    paddingVertical: space.sm,
  },
  side: {
    flex: 1,
    gap: space.lg,
  },
  split: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.xxl,
  },
  tally: {
    gap: space.sm,
  },
  tallyLine: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm + 2,
  },
});
