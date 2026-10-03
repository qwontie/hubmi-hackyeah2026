import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import {
  Check,
  CircleAlert,
  Download,
  MessageSquareText,
  Send,
  Sparkles,
} from "lucide-react-native";
import { useEffect, useRef } from "react";
import {
  Platform,
  type ScrollView,
  StyleSheet,
  type Text,
  View,
} from "react-native";
import type { ApplicationSection, GrantApplication } from "@/api/types";
import { API_BASE, APP_NAME } from "@/config";
import { applicationState } from "@/features/grant-application";
import { Stamp } from "@/features/stamp";
import {
  isPlaceholder,
  sameText,
  useGrantApplication,
} from "@/hooks/use-grants";
import { focusAndAnnounce } from "@/lib/a11y";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const SHORT = 500;
const SENT = "Wniosek wysłany do ROPS";

type Form = ReturnType<typeof useGrantApplication>;

const originLabel = (section: ApplicationSection, draft: string) => {
  if (draft.length === 0) {
    return "";
  }
  if (!sameText(draft, section.text)) {
    return "Twoja odpowiedź";
  }
  return {
    ai: "Podpowiedź AI. Przeczytaj i popraw.",
    author: "Twoja odpowiedź",
    empty: "",
    idea: "Skopiowane z Twojego pomysłu",
  }[section.source];
};

const sectionError = (form: Form, section: ApplicationSection) => {
  const draft = form.drafts[section.key] ?? "";
  if (draft.length > section.max_length) {
    return `Odpowiedź jest za długa. Skróć ją do ${section.max_length} znaków.`;
  }
  if (form.attempted && form.empty.includes(section.key)) {
    return isPlaceholder(section, draft)
      ? "Ta podpowiedź AI mówi tylko, czego brakuje. Wpisz własną odpowiedź."
      : "Odpowiedz na to pytanie, żeby wysłać wniosek.";
  }
  return null;
};

function Question({
  form,
  index,
  section,
}: {
  form: Form;
  index: number;
  section: ApplicationSection;
}) {
  const { colors } = useTheme();
  const draft = form.drafts[section.key] ?? "";
  const origin = originLabel(section, draft);
  const fromAi = origin.startsWith("Podpowiedź AI");
  return (
    <Sheet>
      <View style={styles.head}>
        <Txt mono style={styles.number} tone="stamp" weight="600">
          {String(index + 1).padStart(2, "0")}
        </Txt>
        <Heading level={2} size="h3" style={styles.grow}>
          {section.label}
          {section.required ? "" : " (nieobowiązkowe)"}
        </Heading>
      </View>
      <TextField
        editable={form.busy !== "suggest" && form.busy !== "submit"}
        error={sectionError(form, section)}
        hideLabel
        hint={section.hint || undefined}
        label={section.label}
        multiline
        onChangeText={(text) => form.setDraft(section.key, text)}
        rows={section.max_length <= SHORT ? 2 : 6}
        value={draft}
      />
      {isPlaceholder(section, draft) ? (
        <View style={styles.line}>
          <CircleAlert aria-hidden color={colors.stamp} size={22} />
          <Txt style={styles.grow} variant="detail">
            {`AI nie znalazła tego w Twoich odpowiedziach. Dopisz: ${section.missing.join(", ")}.`}
          </Txt>
        </View>
      ) : null}
      <View style={styles.foot}>
        <View style={styles.origin}>
          {fromAi ? (
            <Sparkles aria-hidden color={colors.stamp} size={18} />
          ) : null}
          <Txt style={styles.grow} tone="soft" variant="small">
            {origin}
          </Txt>
        </View>
        <Txt mono tone="soft" variant="small">
          {`${draft.length} / ${section.max_length}`}
        </Txt>
      </View>
    </Sheet>
  );
}

function Helper({ form }: { form: Form }) {
  return (
    <Sheet>
      <View style={styles.group}>
        <Heading level={2} size="h3">
          Nie wiesz, jak odpowiedzieć?
        </Heading>
        <Txt tone="soft">
          Sztuczna inteligencja może zaproponować tekst w pustych polach, na
          podstawie Twojego pomysłu i tego, co już napiszesz. Twoich odpowiedzi
          nie zmienia. To nieobowiązkowe i trwa do pół minuty.
        </Txt>
      </View>
      <View style={styles.start}>
        <Button
          busy={form.busy === "suggest"}
          disabled={form.busy !== null}
          icon={Sparkles}
          label={
            form.busy === "suggest"
              ? "AI pisze podpowiedzi"
              : "Podpowiedz odpowiedzi (AI)"
          }
          onPress={form.suggest}
        />
      </View>
      {form.suggested ? (
        <Notice tone="info">
          Puste pola wypełniła sztuczna inteligencja. Mają znak „Podpowiedź AI”.
          Przeczytaj je i popraw, zanim wyślesz wniosek.
        </Notice>
      ) : null}
    </Sheet>
  );
}

function Contact({ form }: { form: Form }) {
  return (
    <Sheet>
      <View style={styles.group}>
        <Heading level={2} size="h3">
          Jak ROPS ma Ci odpowiedzieć?
        </Heading>
        <TextField
          autoCapitalize="none"
          autoComplete="email"
          error={form.emailError}
          hint="Nieobowiązkowo. Bez adresu stan wniosku sprawdzisz tylko na tym urządzeniu."
          inputMode="email"
          keyboardType="email-address"
          label="Twój adres e-mail"
          onChangeText={form.setEmail}
          textContentType="emailAddress"
          value={form.email}
        />
        {form.email.trim().length > 0 ? (
          <Checkbox
            checked={form.consent}
            error={form.consentError}
            label="Zgadzam się, żeby ROPS w Krakowie użył tego adresu tylko do kontaktu w sprawie mojego wniosku."
            onChange={form.setConsent}
          />
        ) : null}
      </View>
    </Sheet>
  );
}

const savedLine = (form: Form) => {
  if (form.unsaved) {
    return "Zapisuję zmiany.";
  }
  return form.savedAt
    ? `Wersja robocza zapisana o ${form.savedAt.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" })}.`
    : "Wersja robocza zapisuje się sama.";
};

function Actions({
  form,
  required,
}: {
  form: Form;
  required: ApplicationSection[];
}) {
  const { colors, wide } = useTheme();
  const open = form.empty.length;
  const done = open === 0;
  const Icon = done ? Check : CircleAlert;
  const blocked =
    form.attempted &&
    (open > 0 ||
      form.tooLong.length > 0 ||
      Boolean(form.emailError || form.consentError));
  return (
    <Sheet raised>
      <View style={styles.line}>
        <Icon aria-hidden color={done ? colors.ok : colors.stamp} size={22} />
        <Txt style={styles.grow} weight="500">
          {done
            ? "Wszystkie wymagane pytania mają odpowiedź."
            : `Bez odpowiedzi: ${open} z ${required.length} wymaganych ${pluralPl(required.length, "pytania", "pytań", "pytań")}.`}
        </Txt>
      </View>
      {blocked ? (
        <Notice tone="error">
          Wniosek jeszcze nie został wysłany. Popraw pola zaznaczone na
          czerwono.
        </Notice>
      ) : null}
      {form.error ? <Notice tone="error">{form.error}</Notice> : null}
      <View style={[styles.actions, wide && styles.actionsWide]}>
        <Button
          busy={form.busy === "submit"}
          disabled={form.busy !== null}
          fill={!wide}
          icon={Send}
          label={form.busy === "submit" ? "Wysyłam" : "Wyślij wniosek do ROPS"}
          onPress={form.submit}
          size="large"
          variant="primary"
        />
        <Button
          busy={form.busy === "save"}
          disabled={form.busy !== null}
          fill={!wide}
          label="Zapisz i dokończ później"
          onPress={async () => {
            if (await form.saveNow()) {
              router.navigate("/dzialaj");
            }
          }}
          size="large"
        />
      </View>
      <Txt aria-live="polite" tone="soft" variant="detail">
        {savedLine(form)}
      </Txt>
    </Sheet>
  );
}

function Sent({
  announce,
  application,
}: {
  announce: boolean;
  application: GrantApplication;
}) {
  const { wide } = useTheme();
  const title = useRef<Text>(null);
  useEffect(() => {
    if (!announce) {
      return;
    }
    if (Platform.OS === "web") {
      const element = title.current as unknown as HTMLElement | null;
      if (element) {
        element.setAttribute("tabindex", "-1");
        element.style.scrollMarginTop = "220px";
        element.focus({ preventScroll: true });
        element.scrollIntoView({ block: "start" });
      }
      return;
    }
    focusAndAnnounce(title.current, SENT);
  }, [announce]);
  const { idea } = application;
  return (
    <Sheet raised>
      <View style={[styles.sent, wide && styles.sentWide]}>
        <View style={[styles.group, wide && styles.grow]}>
          <Heading level={2} ref={title}>
            {SENT}
          </Heading>
          <Txt>
            Pracownik ROPS przeczyta wniosek. Jego stan zobaczysz w menu
            Działaj, w części „Moje wnioski”, na tym urządzeniu.
            {application.contact_email
              ? ` Odpowiedź przyjdzie też na adres ${application.contact_email}.`
              : ""}
            {idea ? " ROPS odpisze też w rozmowie o Twoim pomyśle." : ""}
          </Txt>
          <Txt tone="soft">Treści wniosku nie można już zmienić.</Txt>
        </View>
        {application.submitted_at ? (
          <Stamp
            at={new Date(application.submitted_at)}
            number={application.number}
            word="PRZYJĘTO"
          />
        ) : null}
      </View>
      <View style={[styles.actions, wide && styles.actionsWide]}>
        <ExternalLink
          href={`${API_BASE}${application.pdf_url}`}
          icon={Download}
          label="Pobierz wniosek (PDF)"
        />
        {idea ? (
          <Button
            icon={MessageSquareText}
            label="Rozmowa z ROPS o pomyśle"
            onPress={() =>
              router.push({
                params: { id: idea.id },
                pathname: "/pomysl/[id]",
              })
            }
          />
        ) : null}
      </View>
    </Sheet>
  );
}

function Answers({ sections }: { sections: ApplicationSection[] }) {
  const { colors } = useTheme();
  return (
    <Sheet>
      <Heading level={2}>Twoje odpowiedzi</Heading>
      <View role="list">
        {sections.map((section, index) => (
          <View
            key={section.key}
            role="listitem"
            style={[
              styles.answer,
              { borderTopColor: colors.rule },
              index === 0 && styles.first,
            ]}
          >
            <Txt mono style={styles.number} tone="stamp" weight="600">
              {String(index + 1).padStart(2, "0")}
            </Txt>
            <View style={styles.answerText}>
              <Txt weight="600">{section.label}</Txt>
              <Txt tone={section.text ? "default" : "soft"}>
                {section.text || "Bez odpowiedzi."}
              </Txt>
            </View>
          </View>
        ))}
      </View>
    </Sheet>
  );
}

export default function GrantApplicationScreen() {
  const params = useLocalSearchParams<{ id: string; idea?: string }>();
  const form = useGrantApplication(params.id, params.idea);
  const scroll = useRef<ScrollView>(null);
  const { justSent } = form;
  useEffect(() => {
    if (justSent) {
      scroll.current?.scrollTo({ animated: false, y: 0 });
    }
  }, [justSent]);
  if (form.loading) {
    return (
      <Screen back="Nabory" backFallback="/nabory">
        <Txt aria-live="polite">Wczytuję wniosek.</Txt>
      </Screen>
    );
  }
  if (!form.application) {
    return (
      <Screen back="Nabory" backFallback="/nabory">
        <Notice title="Nie udało się otworzyć wniosku" tone="error">
          <View style={styles.group}>
            <Txt>{form.error}</Txt>
            <Button label="Spróbuj ponownie" onPress={form.retry} />
          </View>
        </Notice>
      </Screen>
    );
  }
  const { application } = form;
  const required = application.sections.filter((section) => section.required);
  const hero = (
    <View style={styles.group}>
      <Txt tone="stamp" variant="detail" weight="600">
        {applicationState(application.status, application.submitted_at)}
        {application.call.demo ? " · Nabór pokazowy" : ""}
      </Txt>
      <Heading level={1}>
        {form.editable ? "Twój wniosek" : `Wniosek nr ${application.number}`}
      </Heading>
      <Txt tone="soft" variant="lead">
        {application.call.title}
      </Txt>
      {application.idea ? (
        <Txt tone="soft" variant="detail">
          {`Pomysł: ${application.idea.title}`}
        </Txt>
      ) : null}
    </View>
  );
  return (
    <Screen
      back="Nabory"
      backFallback="/nabory"
      hero={hero}
      ref={scroll}
      width={900}
    >
      <Head>
        <title>{`Wniosek · ${application.call.title} · ${APP_NAME}`}</title>
      </Head>
      {form.editable ? (
        <>
          <Txt variant="lead">
            {application.idea
              ? "Odpowiedzi skopiowaliśmy z Twojego pomysłu. Popraw je i dopisz to, czego brakuje. Na końcu jest jeden przycisk: wyślij."
              : "Odpowiedz na pytania naboru. Na końcu jest jeden przycisk: wyślij."}
          </Txt>
          <Helper form={form} />
          {application.sections.map((section, index) => (
            <Question
              form={form}
              index={index}
              key={section.key}
              section={section}
            />
          ))}
          {application.idea ? null : <Contact form={form} />}
          <Actions form={form} required={required} />
        </>
      ) : (
        <>
          <Sent announce={justSent} application={application} />
          <Answers sections={application.sections} />
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: "flex-start", gap: space.md },
  actionsWide: { alignItems: "center", flexDirection: "row", flexWrap: "wrap" },
  answer: {
    borderTopWidth: 1,
    flexDirection: "row",
    gap: space.md,
    paddingVertical: space.lg,
  },
  answerText: { flex: 1, gap: space.xs },
  first: { borderTopWidth: 0 },
  foot: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.md,
    justifyContent: "space-between",
  },
  group: { gap: space.md },
  grow: { flex: 1 },
  head: { alignItems: "baseline", flexDirection: "row", gap: space.md },
  line: { alignItems: "flex-start", flexDirection: "row", gap: space.sm + 2 },
  number: { minWidth: 32 },
  origin: {
    alignItems: "center",
    flex: 1,
    flexDirection: "row",
    gap: space.xs,
  },
  sent: { alignItems: "flex-start", gap: space.xl },
  sentWide: { flexDirection: "row" },
  start: { alignItems: "flex-start" },
});
