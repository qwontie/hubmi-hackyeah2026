import { router } from "expo-router";
import Head from "expo-router/head";
import { MessageSquareText, RotateCcw, Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { IdeaCreated } from "@/api/types";
import { APP_NAME } from "@/config";
import { IdeaAssistant } from "@/features/idea-assistant";
import { InnovationRow } from "@/features/innovation-row";
import { Stamp } from "@/features/stamp";
import { useIdeaForm } from "@/hooks/use-idea";
import { usePowiats } from "@/hooks/use-powiats";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { PageHead, Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { AccessButton } from "@/ui/shell";
import { Heading, Txt } from "@/ui/text";

function Created({
  created,
  onReset,
}: {
  created: IdeaCreated;
  onReset: () => void;
}) {
  return (
    <Sheet raised>
      <View style={styles.row}>
        <View style={[styles.block, styles.flex]}>
          <Heading level={2}>Pomysł trafił do ROPS</Heading>
          <Txt>
            Pracownicy ROPS przeczytają pomysł. Po akceptacji będzie widoczny
            dla innych.
          </Txt>
        </View>
        <Stamp at={new Date()} number={created.number} word="PRZYJĘTO" />
      </View>
      {created.similar_ideas.length > 0 ? (
        <View style={styles.block}>
          <Heading level={3}>Podobne pomysły innych osób</Heading>
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
          <Heading level={3}>Podobne rozwiązania z biblioteki ROPS</Heading>
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
    </Sheet>
  );
}

export default function IdeaScreen() {
  const powiats = usePowiats();
  const {
    busy,
    canvas,
    created,
    draft,
    error,
    errors,
    form,
    needsConsent,
    options,
    reset,
    round,
    set,
    setCanvas,
    stageOptions,
    submit,
  } = useIdeaForm();

  return (
    <Screen tabs trailing={<AccessButton />}>
      <Head>
        <title>{`Zgłoś pomysł · ${APP_NAME}`}</title>
      </Head>
      {created ? (
        <Created created={created} onReset={reset} />
      ) : (
        <>
          <PageHead>
            <View style={styles.block}>
              <Heading level={1}>
                Masz pomysł na zmianę w swojej okolicy?
              </Heading>
              <Txt tone="soft" variant="lead">
                Opisz go krótko. ROPS w Krakowie przeczyta każdy pomysł.
              </Txt>
            </View>
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
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.lg,
  },
  small: {
    gap: space.xs,
  },
});
