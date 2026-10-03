import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { BookOpen, Copy } from "lucide-react-native";
import { useState } from "react";
import { Platform, StyleSheet, View } from "react-native";
import type { Adaptation } from "@/api/types";
import { APP_NAME } from "@/config";
import { InnovationRow } from "@/features/innovation-row";
import { ReadAloudButton } from "@/features/read-aloud-button";
import { PLAN_LISTS, planSpeech, useAdaptation } from "@/hooks/use-adaptation";
import { formatDate } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
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
          Wczytuję plan…
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
  flex: {
    flex: 1,
  },
  group: {
    gap: space.md,
  },
  list: {
    gap: space.md,
  },
  section: {
    borderTopWidth: 1,
    paddingTop: space.xl,
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
