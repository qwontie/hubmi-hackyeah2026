import Head from "expo-router/head";
import { RotateCcw, Send } from "lucide-react-native";
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { Canvas, IdeaCreated, IdeaOptions, Powiat } from "@/api/types";
import { APP_NAME } from "@/config";
import { IdeaAssistant } from "@/features/idea-assistant";
import { InnovationRow } from "@/features/innovation-row";
import { Stamp } from "@/features/stamp";
import { saveIdea } from "@/storage/ideas";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

type Field =
  | "title"
  | "essence"
  | "for_whom"
  | "contact_email"
  | "contact_consent";
type Errors = Partial<Record<Field, string | null>>;

interface Form {
  consent: boolean;
  email: string;
  essence: string;
  forWhom: string;
  powiat: string;
  stage: string;
  title: string;
}

const emptyForm: Form = {
  consent: false,
  email: "",
  essence: "",
  forWhom: "",
  powiat: "",
  stage: "idea",
  title: "",
};

const validate = (form: Form): Errors => {
  const email = form.email.trim();
  return {
    contact_consent:
      email.length > 0 && !form.consent
        ? "Zaznacz zgodę, żeby ROPS mógł odpisać na ten adres."
        : null,
    contact_email:
      email.length > 0 && !EMAIL.test(email)
        ? "Ten adres wygląda na niepełny. Sprawdź go, np. jan@poczta.pl."
        : null,
    essence:
      form.essence.trim().length < 20
        ? "Opisz pomysł w co najmniej 20 znakach."
        : null,
    for_whom:
      form.forWhom.trim().length < 3 ? "Napisz, dla kogo jest pomysł." : null,
    title:
      form.title.trim().length < 5
        ? "Nazwij pomysł w co najmniej 5 znakach."
        : null,
  };
};

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
            Pracownicy ROPS przeczytają fiszkę. Po akceptacji pomysł będzie
            widoczny dla innych.
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
        icon={RotateCcw}
        label="Zgłoś kolejny pomysł"
        onPress={onReset}
        variant="quiet"
      />
    </Sheet>
  );
}

export default function IdeaScreen() {
  const [options, setOptions] = useState<IdeaOptions | null>(null);
  const [powiats, setPowiats] = useState<Powiat[]>([]);
  const [form, setForm] = useState<Form>(emptyForm);
  const [canvas, setCanvas] = useState<Partial<Canvas>>({});
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<IdeaCreated | null>(null);
  const [round, setRound] = useState(0);

  useEffect(() => {
    const abort = new AbortController();
    api
      .ideaOptions(abort.signal)
      .then(setOptions)
      .catch(() => setOptions(null));
    api
      .powiats(abort.signal)
      .then(setPowiats)
      .catch(() => setPowiats([]));
    return () => abort.abort();
  }, []);

  const set = (patch: Partial<Form>) =>
    setForm((current) => ({ ...current, ...patch }));

  const submit = async () => {
    const problems = validate(form);
    setErrors(problems);
    if (Object.values(problems).some(Boolean)) {
      return;
    }
    const email = form.email.trim();
    setBusy(true);
    setError(null);
    try {
      const result = await api.createIdea({
        essence: form.essence.trim(),
        for_whom: form.forWhom.trim(),
        stage: form.stage,
        title: form.title.trim(),
        ...(Object.keys(canvas).length > 0 ? { canvas } : {}),
        ...(form.powiat ? { powiat: form.powiat } : {}),
        ...(email ? { contact_consent: true, contact_email: email } : {}),
      });
      await saveIdea({
        createdAt: new Date().toISOString(),
        id: result.id,
        number: result.number,
        title: form.title.trim(),
        token: result.edit_token,
      }).catch(() => undefined);
      setCreated(result);
    } catch (caught) {
      if (caught instanceof ApiError) {
        const next: Errors = {};
        for (const field of caught.fields) {
          next[field.field as Field] = field.message;
        }
        setErrors(next);
      }
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setForm(emptyForm);
    setCanvas({});
    setCreated(null);
    setErrors({});
    setRound((value) => value + 1);
  };

  return (
    <Screen>
      <Head>
        <title>{`Zgłoś pomysł · ${APP_NAME}`}</title>
      </Head>
      {created ? (
        <Created created={created} onReset={reset} />
      ) : (
        <>
          <Sheet raised>
            <View style={styles.block}>
              <Heading level={1}>
                Masz pomysł na zmianę w swojej okolicy?
              </Heading>
              <Txt tone="soft" variant="lead">
                Opisz go krótko. ROPS w Krakowie przeczyta każdą fiszkę.
              </Txt>
            </View>
            <TextField
              error={errors.title}
              label="Nazwa pomysłu"
              maxLength={120}
              onChangeText={(value) => set({ title: value })}
              placeholder="Na przykład: Wspólne obiady dla seniorów"
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
              placeholder="Na przykład: samotni seniorzy w małej wsi"
              value={form.forWhom}
            />
            {options ? (
              <Select
                label="Na jakim etapie jest pomysł?"
                onChange={(value) => set({ stage: value })}
                options={options.stages.map((item) => ({
                  label: item.name,
                  value: item.slug,
                }))}
                value={form.stage}
              />
            ) : null}
          </Sheet>

          {options ? (
            <Sheet>
              <IdeaAssistant
                canvas={canvas}
                draft={{
                  essence: form.essence.trim() || undefined,
                  for_whom: form.forWhom.trim() || undefined,
                  stage: form.stage,
                  title: form.title.trim() || undefined,
                }}
                key={round}
                onCanvas={setCanvas}
                options={options}
              />
            </Sheet>
          ) : null}

          <Sheet>
            <Heading level={2}>Wyślij pomysł</Heading>
            {powiats.length > 0 ? (
              <Select
                emptyLabel="Nie wybieram"
                label="Powiat"
                onChange={(value) => set({ powiat: value })}
                optional
                options={powiats.map((item) => ({
                  label: item.name,
                  value: item.slug,
                }))}
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
            {form.email.trim().length > 0 ? (
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
              label={busy ? "Wysyłam…" : "Wyślij pomysł do ROPS"}
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
