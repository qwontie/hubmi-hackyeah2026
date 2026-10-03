import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { StyleSheet, View } from "react-native";
import { API_BASE, APP_NAME } from "@/config";
import { useGrantApplication } from "@/hooks/use-grants";
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
  return (
    <Screen back="Nabór" width={900}>
      <Head>
        <title>{`Wniosek nr ${application.number} · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        <Txt tone="stamp" weight="600">
          {statusLabel[application.status]}
        </Txt>
        <Heading level={1}>Wniosek nr {application.number}</Heading>
        <Txt tone="soft">
          {application.call.title} · pomysł {application.idea.title}
        </Txt>
        {application.call.demo ? <Txt weight="600">Nabór pokazowy</Txt> : null}
      </View>
      {form.error ? <Notice tone="error">{form.error}</Notice> : null}
      {application.sections.map((section) => (
        <Sheet key={section.key}>
          <View style={styles.group}>
            <Heading level={2}>{section.label}</Heading>
            <TextField
              editable={!readOnly}
              error={
                section.required && !form.drafts[section.key]?.trim()
                  ? "Ta sekcja jest wymagana."
                  : null
              }
              hint={section.hint || undefined}
              label={section.label}
              maxLength={section.max_length}
              multiline
              onChangeText={(text) => form.setDraft(section.key, text)}
              value={form.drafts[section.key] ?? ""}
            />
            <Txt tone="soft" variant="small">
              {(form.drafts[section.key] ?? "").length} / {section.max_length}
            </Txt>
            {section.missing.length > 0 ? (
              <Notice live={false} title="Do uzupełnienia" tone="info">
                {section.missing.join(", ")}
              </Notice>
            ) : null}
          </View>
        </Sheet>
      ))}
      {readOnly ? (
        <Notice title="Wniosek jest tylko do odczytu" tone="success">
          Po złożeniu nie można już zmieniać treści.
        </Notice>
      ) : (
        <View style={styles.actions}>
          <Button
            busy={form.busy === "save"}
            disabled={form.busy !== null}
            label="Zapisz wersję roboczą"
            onPress={form.save}
          />
          <Button
            busy={form.busy === "redraft"}
            disabled={form.busy !== null}
            label="Ponów szkic AI"
            onPress={form.redraft}
            variant="secondary"
          />
          <Button
            busy={form.busy === "submit"}
            disabled={
              form.busy !== null || application.missing_required.length > 0
            }
            label="Złóż wniosek"
            onPress={form.submit}
            variant="primary"
          />
          {application.missing_required.length > 0 ? (
            <Txt aria-live="polite" tone="soft">
              Uzupełnij wymagane informacje przed złożeniem.
            </Txt>
          ) : null}
        </View>
      )}
      <ExternalLink
        href={`${API_BASE}${application.pdf_url}`}
        label="Pobierz PDF wniosku"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: "flex-start", gap: space.md },
  group: { gap: space.md },
});
