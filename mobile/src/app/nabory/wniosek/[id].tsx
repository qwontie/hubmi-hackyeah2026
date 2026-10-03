import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { Check, CircleAlert, Download, Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { ApplicationSection } from "@/api/types";
import { API_BASE, APP_NAME } from "@/config";
import { useGrantApplication } from "@/hooks/use-grants";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { ExternalLink } from "@/ui/external-link";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const statusLabel = {
  accepted: "Przyjęty",
  draft: "Wersja robocza",
  in_review: "W ocenie",
  rejected: "Odrzucony",
  submitted: "Złożony",
} as const;

const SHORT = 500;

type Form = ReturnType<typeof useGrantApplication>;

const sourceLabel = (draft: string, untouched: boolean) => {
  if (draft.length === 0) {
    return "";
  }
  return untouched ? "Szkic AI" : "Twoja wersja";
};

function Progress({ open, total }: { open: number; total: number }) {
  const { colors } = useTheme();
  const done = open === 0;
  const Icon = done ? Check : CircleAlert;
  return (
    <View style={styles.line}>
      <Icon aria-hidden color={done ? colors.ok : colors.stamp} size={22} />
      <Txt style={styles.grow} weight="500">
        {done
          ? "Wszystkie wymagane sekcje są wypełnione."
          : `Do uzupełnienia: ${open} z ${total} sekcji.`}
      </Txt>
    </View>
  );
}

function SectionCard({
  draft,
  index,
  onChange,
  readOnly,
  section,
}: {
  draft: string;
  index: number;
  onChange: (text: string) => void;
  readOnly: boolean;
  section: ApplicationSection;
}) {
  const { colors } = useTheme();
  const untouched = section.source === "ai" && draft === section.text;
  return (
    <Sheet>
      <View style={styles.head}>
        <Txt mono style={styles.number} tone="stamp" weight="600">
          {String(index + 1).padStart(2, "0")}
        </Txt>
        <Heading level={2} size="h3" style={styles.grow}>
          {section.label}
        </Heading>
      </View>
      <TextField
        editable={!readOnly}
        error={
          section.required && !draft.trim() ? "Ta sekcja jest wymagana." : null
        }
        hideLabel
        hint={section.hint || undefined}
        label={section.label}
        maxLength={section.max_length}
        multiline
        onChangeText={onChange}
        rows={section.max_length <= SHORT ? 2 : 6}
        value={draft}
      />
      <View style={styles.foot}>
        <Txt tone="soft" variant="small">
          {sourceLabel(draft, untouched)}
        </Txt>
        <Txt mono tone="soft" variant="small">
          {`${draft.length} / ${section.max_length}`}
        </Txt>
      </View>
      {section.missing.length > 0 ? (
        <View style={styles.line}>
          <CircleAlert aria-hidden color={colors.stamp} size={22} />
          <Txt style={styles.grow} variant="detail">
            {`Do uzupełnienia: ${section.missing.join(", ")}.`}
          </Txt>
        </View>
      ) : null}
    </Sheet>
  );
}

function Actions({ form }: { form: Form }) {
  const { wide } = useTheme();
  return (
    <Sheet raised>
      <View style={[styles.actions, wide && styles.actionsWide]}>
        <Button
          busy={form.busy === "submit"}
          disabled={form.busy !== null || !form.canSubmit}
          fill={!wide}
          icon={Send}
          label="Złóż wniosek"
          onPress={form.submit}
          size="large"
          variant="primary"
        />
        <Button
          busy={form.busy === "save"}
          disabled={form.busy !== null || !form.dirty}
          fill={!wide}
          label="Zapisz wersję roboczą"
          onPress={form.save}
          size="large"
        />
        <Button
          busy={form.busy === "redraft"}
          disabled={form.busy !== null}
          label="Przygotuj szkic od nowa"
          onPress={form.redraft}
          size="large"
          variant="quiet"
        />
      </View>
      {form.canSubmit ? null : (
        <Txt aria-live="polite" tone="soft">
          Uzupełnij wymagane informacje przed złożeniem.
        </Txt>
      )}
    </Sheet>
  );
}

export default function GrantApplicationScreen() {
  const params = useLocalSearchParams<{ id: string; idea: string }>();
  const form = useGrantApplication(params.id, params.idea);
  if (form.loading) {
    return (
      <Screen back="Nabór">
        <Txt aria-live="polite">Wczytuję wniosek.</Txt>
      </Screen>
    );
  }
  if (!form.application) {
    return (
      <Screen back="Nabór">
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
  const readOnly = application.status !== "draft";
  const required = application.sections.filter((section) => section.required);
  const open = required.filter(
    (section) => !(form.drafts[section.key] ?? "").trim()
  ).length;
  const hero = (
    <View style={styles.group}>
      <Txt tone="stamp" variant="detail" weight="600">
        {statusLabel[application.status]}
        {application.call.demo ? " · Nabór pokazowy" : ""}
      </Txt>
      <Heading level={1}>{`Wniosek nr ${application.number}`}</Heading>
      <Txt tone="soft" variant="lead">
        {application.idea.title}
      </Txt>
      <Txt tone="soft" variant="detail">
        {application.call.title}
      </Txt>
    </View>
  );
  return (
    <Screen back="Nabór" hero={hero} width={900}>
      <Head>
        <title>{`Wniosek nr ${application.number} · ${APP_NAME}`}</title>
      </Head>
      {form.error ? <Notice tone="error">{form.error}</Notice> : null}
      {readOnly ? null : (
        <View style={styles.group}>
          <Notice live={false} tone="info">
            Szkic przygotowała sztuczna inteligencja na podstawie Twojego
            pomysłu. Przeczytaj każdą sekcję i popraw ją, zanim złożysz wniosek.
          </Notice>
          <Progress open={open} total={required.length} />
        </View>
      )}
      {application.sections.map((section, index) => (
        <SectionCard
          draft={form.drafts[section.key] ?? ""}
          index={index}
          key={section.key}
          onChange={(text) => form.setDraft(section.key, text)}
          readOnly={readOnly}
          section={section}
        />
      ))}
      {readOnly ? (
        <Notice title="Wniosek jest tylko do odczytu" tone="success">
          Po złożeniu nie można już zmieniać treści.
        </Notice>
      ) : (
        <Actions form={form} />
      )}
      <View style={styles.start}>
        <ExternalLink
          href={`${API_BASE}${application.pdf_url}`}
          icon={Download}
          label="Pobierz PDF wniosku"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: "flex-start", gap: space.md },
  actionsWide: { alignItems: "center", flexDirection: "row", flexWrap: "wrap" },
  foot: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  group: { gap: space.md },
  grow: { flex: 1 },
  head: { alignItems: "baseline", flexDirection: "row", gap: space.md },
  line: { alignItems: "flex-start", flexDirection: "row", gap: space.sm + 2 },
  number: { minWidth: 32 },
  start: { alignItems: "flex-start" },
});
