import { router } from "expo-router";
import Head from "expo-router/head";
import { MessageSquareText, RotateCcw, Send } from "lucide-react-native";
import { useEffect, useRef } from "react";
import { type ScrollView, StyleSheet, type Text, View } from "react-native";
import type { IdeaCreated } from "@/api/types";
import { APP_NAME } from "@/config";
import { IdeaAssistant } from "@/features/idea-assistant";
import { IdeaGrantAction } from "@/features/idea-visualisation";
import { InnovationRow } from "@/features/innovation-row";
import { PrivacyNote } from "@/features/privacy-note";
import { Stamp } from "@/features/stamp";
import { useIdeaForm } from "@/hooks/use-idea";
import { usePowiats } from "@/hooks/use-powiats";
import { focusAndAnnounce } from "@/lib/a11y";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const SENT = "Pomysł trafił do ROPS";

function Created({
  created,
  hasEmail,
  onReset,
}: {
  created: IdeaCreated;
  hasEmail: boolean;
  onReset: () => void;
}) {
  const { wide } = useTheme();
  const title = useRef<Text>(null);
  useEffect(() => {
    focusAndAnnounce(title.current, SENT);
  }, []);
  return (
    <Sheet raised>
      <View style={[styles.sent, wide && styles.sentWide]}>
        <View style={[styles.block, wide && styles.flex]}>
          <Heading level={1} ref={title} size="h2">
            {SENT}
          </Heading>
          <Txt>
            {hasEmail
              ? "Pracownik ROPS przeczyta pomysł i odpisze: w rozmowie na tej stronie i na Twój adres e-mail."
              : "Pracownik ROPS przeczyta pomysł i odpisze w rozmowie na tej stronie. Otworzysz ją z menu Działaj, w części „Moje pomysły”, na tym urządzeniu."}
          </Txt>
        </View>
        <Stamp at={new Date()} number={created.number} word="PRZYJĘTO" />
      </View>
      {created.similar_ideas.length > 0 ? (
        <View style={styles.block}>
          <Heading level={2} size="h3">
            Podobne pomysły innych osób
          </Heading>
          {created.similar_ideas.map((idea) => (
            <View key={idea.id} style={styles.small}>
              <Txt weight="600">{idea.title}</Txt>
              <Txt tone="soft">{idea.essence}</Txt>
            </View>
          ))}
        </View>
      ) : null}
      {created.similar_innovations.length > 0 ? (
        <View style={styles.block}>
          <Heading level={2} size="h3">
            Podobne rozwiązania z biblioteki ROPS
          </Heading>
          <View role="list">
            {created.similar_innovations.map((item, index) => (
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
                last={index === created.similar_innovations.length - 1}
              />
            ))}
          </View>
        </View>
      ) : null}
      <View style={styles.row}>
        <Button
          icon={MessageSquareText}
          label="Rozmowa z ROPS o tym pomyśle"
          onPress={() =>
            router.push({
              params: { id: created.id },
              pathname: "/pomysl/[id]",
            })
          }
        />
        <Button
          icon={RotateCcw}
          label="Zgłoś kolejny pomysł"
          onPress={onReset}
          variant="quiet"
        />
      </View>
    </Sheet>
  );
}

export default function IdeaScreen() {
  const { colors } = useTheme();
  const powiats = usePowiats();
  const {
    busy,
    canvas,
    created,
    draft,
    clearProblem,
    error,
    errors,
    form,
    needsConsent,
    options,
    problem,
    reset,
    round,
    set,
    setCanvas,
    stageOptions,
    submit,
  } = useIdeaForm();
  const scroll = useRef<ScrollView>(null);
  const sent = Boolean(created);

  useEffect(() => {
    if (sent) {
      scroll.current?.scrollTo({ animated: false, y: 0 });
    }
  }, [sent]);

  return (
    <Screen back="Działaj" backFallback="/dzialaj" ref={scroll}>
      <Head>
        <title>{`Zgłoś pomysł · ${APP_NAME}`}</title>
      </Head>
      {created ? (
        <>
          <Created
            created={created}
            hasEmail={form.email.trim().length > 0}
            onReset={reset}
          />
          <IdeaGrantAction id={created.id} />
        </>
      ) : (
        <>
          <PageHead>
            <View style={styles.block}>
              <Heading level={1}>
                {problem ? "Twój pomysł na ten problem" : "Opisz swój pomysł"}
              </Heading>
              <Txt tone="soft" variant="lead">
                ROPS w Krakowie przeczyta każdy pomysł.
              </Txt>
            </View>
            {problem ? (
              <View style={[styles.problem, { backgroundColor: colors.tone }]}>
                <Txt style={styles.flex} weight="600">
                  {problem.title}
                </Txt>
                <Button
                  label="Inny temat"
                  onPress={clearProblem}
                  variant="quiet"
                />
              </View>
            ) : null}
          </PageHead>
          <Sheet>
            <TextField
              error={errors.title}
              label="Nazwa pomysłu"
              maxLength={120}
              onChangeText={(value) => set({ title: value })}
              placeholder="np. Wspólne obiady"
              value={form.title}
            />
            <TextField
              error={errors.essence}
              label="Na czym polega pomysł?"
              maxLength={2000}
              multiline
              onChangeText={(value) => set({ essence: value })}
              value={form.essence}
            />
            <TextField
              error={errors.for_whom}
              label="Dla kogo jest ten pomysł?"
              maxLength={500}
              onChangeText={(value) => set({ forWhom: value })}
              placeholder="np. samotni seniorzy na wsi"
              value={form.forWhom}
            />
            {options ? (
              <Select
                label="Na jakim etapie jest pomysł?"
                onChange={(value) => set({ stage: value })}
                options={stageOptions}
                value={form.stage}
              />
            ) : null}
          </Sheet>

          {options ? (
            <Sheet>
              <IdeaAssistant
                canvas={canvas}
                draft={draft}
                key={round}
                onCanvas={setCanvas}
                options={options}
              />
            </Sheet>
          ) : null}

          <Sheet>
            <Heading level={2}>Wyślij pomysł</Heading>
            {powiats.options.length > 0 ? (
              <Select
                emptyLabel="Nie wybieram"
                label="Powiat"
                onChange={(value) => set({ powiat: value })}
                optional
                options={powiats.options}
                value={form.powiat}
              />
            ) : null}
            <TextField
              autoCapitalize="none"
              autoComplete="email"
              error={errors.contact_email}
              hint="Nieobowiązkowo. Podaj, jeśli chcesz, żeby ROPS się odezwał."
              inputMode="email"
              keyboardType="email-address"
              label="Twój adres e-mail"
              onChangeText={(value) => set({ email: value })}
              textContentType="emailAddress"
              value={form.email}
            />
            {needsConsent ? (
              <Checkbox
                checked={form.consent}
                error={errors.contact_consent}
                label="Zgadzam się, żeby ROPS w Krakowie użył tego adresu tylko do kontaktu w sprawie mojego pomysłu."
                onChange={(value) => set({ consent: value })}
              />
            ) : null}
            <PrivacyNote />
            {error ? <Notice tone="error">{error}</Notice> : null}
            <Button
              busy={busy}
              icon={Send}
              label={busy ? "Wysyłam" : "Wyślij pomysł do ROPS"}
              onPress={submit}
              size="large"
              variant="primary"
            />
          </Sheet>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  block: {
    gap: space.md,
  },
  flex: {
    flex: 1,
  },
  problem: {
    alignItems: "center",
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.md,
    paddingLeft: space.lg + 2,
    paddingRight: space.sm,
    paddingVertical: space.sm,
  },
  row: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  sent: {
    alignItems: "flex-start",
    gap: space.xl,
  },
  sentWide: {
    flexDirection: "row",
  },
  small: {
    gap: space.xs,
  },
});
