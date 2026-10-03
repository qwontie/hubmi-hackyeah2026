import { Link, router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { ArrowRight, BookOpen, Copy } from "lucide-react-native";
import { useState } from "react";
import { Linking, Platform, Pressable, StyleSheet, View } from "react-native";
import type { Adaptation, LocalChallenge, LocalFact } from "@/api/types";
import { APP_NAME } from "@/config";
import { InnovationRow } from "@/features/innovation-row";
import { ReadAloudButton } from "@/features/read-aloud-button";
import { PLAN_LISTS, planSpeech, useAdaptation } from "@/hooks/use-adaptation";
import { formatDate } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

function Bullets({ items }: { items: string[] }) {
  const { colors } = useTheme();
  return (
    <View role="list" style={styles.list}>
      {items.map((item) => (
        <View key={item} role="listitem" style={styles.bulletRow}>
          <View
            aria-hidden
            style={[styles.bullet, { backgroundColor: colors.stamp }]}
          />
          <Txt style={styles.flex}>{item}</Txt>
        </View>
      ))}
    </View>
  );
}

function CopyLink({ path }: { path: string }) {
  const [copied, setCopied] = useState(false);
  if (Platform.OS !== "web" || typeof navigator === "undefined") {
    return null;
  }
  const url = `${window.location.origin}${path}`;
  return (
    <View style={styles.group}>
      <Button
        icon={Copy}
        label="Skopiuj link do planu"
        onPress={() => {
          navigator.clipboard
            .writeText(url)
            .then(() => setCopied(true))
            .catch(() => setCopied(false));
        }}
      />
      <View aria-live="polite">
        {copied ? (
          <Txt tone="ok" weight="500">
            Skopiowano. Link otwiera ten sam plan bez logowania.
          </Txt>
        ) : null}
      </View>
    </View>
  );
}

const amount = (value: number, unit: string) => {
  const number = value.toLocaleString("pl-PL");
  if (!unit) {
    return number;
  }
  return unit === "%" ? `${number}%` : `${number}\u00a0${unit}`;
};

function Source({
  href,
  page,
  title,
}: {
  href: string;
  page: string;
  title: string;
}) {
  const [hovered, setHovered] = useState(false);
  const webProps =
    Platform.OS === "web"
      ? { href, hrefAttrs: { rel: "noopener noreferrer", target: "_blank" } }
      : {};
  return (
    <Pressable
      accessibilityHint="Otwiera się w nowym oknie"
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={
        Platform.OS === "web"
          ? undefined
          : () => {
              Linking.openURL(href).catch(() => undefined);
            }
      }
      role="link"
      style={styles.source}
      {...webProps}
    >
      <Txt
        style={{ textDecorationLine: hovered ? "underline" : "none" }}
        tone="stamp"
        variant="detail"
        weight="500"
      >
        {`Źródło: ${title}${page}`}
      </Txt>
    </Pressable>
  );
}

function Fact({ fact, first }: { fact: LocalFact; first: boolean }) {
  const { colors } = useTheme();
  return (
    <View
      role="listitem"
      style={[
        styles.fact,
        { borderTopColor: colors.rule },
        first && styles.first,
      ]}
    >
      <Txt>{fact.label}</Txt>
      <View style={styles.figure}>
        <Txt mono variant="h3" weight="600">
          {amount(fact.value, fact.unit)}
        </Txt>
        <Txt tone="soft" variant="detail">
          {fact.region_value === null
            ? `${fact.year}`
            : `${fact.year}\u00a0· w całej Małopolsce ${amount(fact.region_value, fact.unit)}`}
        </Txt>
      </View>
      <Source
        href={fact.source_url}
        page={fact.page ? `, s.\u00a0${fact.page}` : ""}
        title={fact.source_title}
      />
    </View>
  );
}

function Challenge({ challenge }: { challenge: LocalChallenge }) {
  const { colors } = useTheme();
  return (
    <View role="listitem" style={styles.stepBody}>
      <Txt weight="600">{challenge.title}</Txt>
      <Txt tone="soft">{challenge.summary}</Txt>
      <Link
        asChild
        href={{ params: { slug: challenge.slug }, pathname: "/wiedza/[slug]" }}
      >
        <Pressable
          aria-label={`Zobacz wyzwanie: ${challenge.title}`}
          role="link"
          style={styles.more}
        >
          <Txt tone="stamp" variant="detail" weight="600">
            Zobacz wyzwanie
          </Txt>
          <ArrowRight aria-hidden color={colors.stamp} size={20} />
        </Pressable>
      </Link>
    </View>
  );
}

function RopsData({ adaptation }: { adaptation: Adaptation }) {
  const { colors } = useTheme();
  const { plan } = adaptation;
  const facts = plan.local_facts ?? [];
  const challenges = plan.regional_challenges ?? [];
  if (facts.length === 0 && challenges.length === 0 && !plan.local_context) {
    return null;
  }
  return (
    <Sheet>
      <View style={styles.group}>
        <Heading level={2}>
          {adaptation.powiat ? "Dane ROPS dla tego powiatu" : "Dane ROPS"}
        </Heading>
        {plan.local_context ? <Txt>{plan.local_context}</Txt> : null}
      </View>
      {facts.length > 0 ? (
        <View role="list">
          {facts.map((fact, index) => (
            <Fact
              fact={fact}
              first={index === 0}
              key={`${fact.label}-${fact.year}`}
            />
          ))}
        </View>
      ) : null}
      {challenges.length > 0 ? (
        <View
          style={[
            styles.group,
            styles.section,
            { borderTopColor: colors.rule },
          ]}
        >
          <Heading level={3}>Powiązane wyzwania Małopolski</Heading>
          <View role="list" style={styles.list}>
            {challenges.map((challenge) => (
              <Challenge challenge={challenge} key={challenge.slug} />
            ))}
          </View>
        </View>
      ) : null}
    </Sheet>
  );
}

function Plan({ adaptation }: { adaptation: Adaptation }) {
  const { colors } = useTheme();
  const { plan } = adaptation;
  return (
    <>
      <Sheet raised>
        <View style={styles.group}>
          <Heading level={1}>{plan.service_name}</Heading>
          <Txt tone="soft" variant="detail">
            {`${adaptation.institution.name}, ${adaptation.place} · na podstawie rozwiązania „${adaptation.innovation.title}” · ${formatDate(adaptation.created_at)}`}
          </Txt>
        </View>
        <Txt variant="lead">{plan.summary}</Txt>
        <View style={styles.actions}>
          <ReadAloudButton text={planSpeech(plan)} />
          <CopyLink path={adaptation.share_path} />
        </View>
      </Sheet>

      <RopsData adaptation={adaptation} />

      <Sheet>
        <View style={styles.group}>
          <Heading level={2}>Dla kogo</Heading>
          <Txt>{plan.target_group}</Txt>
        </View>
        {plan.steps.length > 0 ? (
          <View style={styles.group}>
            <Heading level={2}>Jak zacząć</Heading>
            <View role="list" style={styles.list}>
              {plan.steps.map((step, index) => (
                <View key={step.title} role="listitem" style={styles.step}>
                  <Txt aria-hidden mono tone="stamp">
                    {index + 1}
                  </Txt>
                  <View style={[styles.flex, styles.stepBody]}>
                    <Txt weight="600">{step.title}</Txt>
                    <Txt>{step.description}</Txt>
                  </View>
                </View>
              ))}
            </View>
          </View>
        ) : null}
        {PLAN_LISTS.map(({ key, title }) => {
          const items = plan[key] as string[];
          return items.length > 0 ? (
            <View
              key={key}
              style={[
                styles.group,
                styles.section,
                { borderTopColor: colors.rule },
              ]}
            >
              <Heading level={2}>{title}</Heading>
              <Bullets items={items} />
            </View>
          ) : null;
        })}
        {plan.risks.length > 0 ? (
          <View
            style={[
              styles.group,
              styles.section,
              { borderTopColor: colors.rule },
            ]}
          >
            <Heading level={2}>Ryzyka</Heading>
            <View role="list" style={styles.list}>
              {plan.risks.map((item) => (
                <View key={item.risk} role="listitem" style={styles.stepBody}>
                  <Txt weight="600">{item.risk}</Txt>
                  <Txt>{`Jak temu zapobiec: ${item.mitigation}`}</Txt>
                </View>
              ))}
            </View>
          </View>
        ) : null}
      </Sheet>

      {plan.combine.length > 0 ? (
        <Sheet>
          <Heading level={2}>Połącz z innymi innowacjami</Heading>
          <View role="list">
            {plan.combine.map((item, index) => (
              <InnovationRow
                innovation={{
                  category: { name: "", slug: "" },
                  has_materials: false,
                  has_video: false,
                  lead: item.lead,
                  slug: item.slug,
                  title: item.title,
                }}
                key={item.slug}
                last={index === plan.combine.length - 1}
                reason={item.why}
              />
            ))}
          </View>
        </Sheet>
      ) : null}
    </>
  );
}

export default function AdaptationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { state: load } = useAdaptation(id);

  return (
    <Screen back="Wróć" backFallback="/biblioteka">
      <Head>
        <title>
          {load.kind === "done"
            ? `${load.data.plan.service_name} · ${APP_NAME}`
            : `Plan usługi · ${APP_NAME}`}
        </title>
      </Head>
      {load.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję plan.
        </Txt>
      ) : null}
      {load.kind === "error" ? (
        <Notice
          title={
            load.missing
              ? "Nie ma takiego planu"
              : "Nie udało się wczytać planu"
          }
          tone="error"
        >
          <View style={styles.group}>
            <Txt>
              {load.missing
                ? "Link może być niepełny. Poproś o niego jeszcze raz."
                : load.message}
            </Txt>
            <Button
              icon={BookOpen}
              label="Przejdź do biblioteki"
              onPress={() => router.replace("/biblioteka")}
            />
          </View>
        </Notice>
      ) : null}
      {load.kind === "done" ? <Plan adaptation={load.data} /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.md,
  },
  bullet: {
    borderRadius: 4,
    height: 7,
    marginTop: 11,
    width: 7,
  },
  bulletRow: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
  },
  fact: {
    borderTopWidth: 1,
    gap: space.xs,
    paddingBottom: space.sm,
    paddingTop: space.md,
  },
  figure: {
    alignItems: "baseline",
    columnGap: space.md,
    flexDirection: "row",
    flexWrap: "wrap",
  },
  first: {
    borderTopWidth: 0,
    paddingTop: 0,
  },
  flex: {
    flex: 1,
  },
  group: {
    gap: space.md,
  },
  list: {
    gap: space.md,
  },
  more: {
    alignItems: "center",
    alignSelf: "flex-start",
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
  },
  section: {
    borderTopWidth: 1,
    paddingTop: space.xl,
  },
  source: {
    alignSelf: "flex-start",
    justifyContent: "center",
    minHeight: minTarget,
  },
  step: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
  },
  stepBody: {
    gap: space.xs,
  },
});
