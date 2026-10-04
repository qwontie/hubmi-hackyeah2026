import { useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { ExpertAnswerView, PublicIdea } from "@/api/types";
import { APP_NAME } from "@/config";
import { PrivacyNote } from "@/features/privacy-note";
import { Trap } from "@/features/trap";
import { useExpertAnswer } from "@/hooks/use-expert-answer";
import { formatDate } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

function Case({ view }: { view: ExpertAnswerView }) {
  if (view.kind === "idea") {
    const idea = view.item as PublicIdea;
    return (
      <>
        <View style={styles.group}>
          <Txt variant="label" weight="600">
            Na czym polega pomysł
          </Txt>
          <Txt>{idea.essence}</Txt>
        </View>
        <View style={styles.group}>
          <Txt variant="label" weight="600">
            Dla kogo
          </Txt>
          <Txt>{idea.for_whom}</Txt>
        </View>
      </>
    );
  }
  return (
    <View style={styles.group}>
      <Txt variant="label" weight="600">
        Opis mieszkańca
      </Txt>
      <Txt>{"text" in view.item ? view.item.text : ""}</Txt>
    </View>
  );
}

function Earlier({ view }: { view: ExpertAnswerView }) {
  const { colors } = useTheme();
  if (view.answers.length === 0) {
    return null;
  }
  return (
    <Sheet>
      <Heading level={2}>Twoje wcześniejsze odpowiedzi</Heading>
      <View role="list">
        {view.answers.map((answer, index) => (
          <View
            key={answer.id}
            role="listitem"
            style={[
              styles.answer,
              index > 0 && { borderTopColor: colors.rule, borderTopWidth: 1 },
            ]}
          >
            <Txt tone="soft" variant="detail">
              {formatDate(answer.created_at)}
            </Txt>
            <Txt>{answer.body}</Txt>
          </View>
        ))}
      </View>
    </Sheet>
  );
}

export default function ExpertAnswerScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const expert = useExpertAnswer(id);
  const { load } = expert;
  return (
    <Screen title="Prośba ROPS o opinię">
      <Head>
        <title>{`Prośba o opinię · ${APP_NAME}`}</title>
      </Head>

      {load.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję sprawę.
        </Txt>
      ) : null}

      {load.kind === "missing" ? (
        <Notice title="Ten link nie działa" tone="error">
          Otwórz stronę linkiem z wiadomości e-mail od ROPS. Jeśli link nadal
          nie działa, odpisz na tę wiadomość.
        </Notice>
      ) : null}

      {load.kind === "error" ? (
        <Notice title="Nie udało się wczytać sprawy" tone="error">
          {load.message}
        </Notice>
      ) : null}

      {load.kind === "ready" ? (
        <>
          <Sheet raised>
            <View style={styles.group}>
              <Txt tone="soft" variant="label">
                {load.view.kind === "idea"
                  ? "Pomysł mieszkańca"
                  : "Zgłoszenie mieszkańca"}
              </Txt>
              <Heading level={2}>{load.view.title}</Heading>
            </View>
            <Case view={load.view} />
            {load.view.note ? (
              <View style={styles.group}>
                <Txt variant="label" weight="600">
                  O co pyta ROPS
                </Txt>
                <Txt>{load.view.note}</Txt>
              </View>
            ) : null}
          </Sheet>

          <Earlier view={load.view} />

          <Sheet>
            <Heading level={2}>Twoja odpowiedź</Heading>
            <TextField
              error={expert.fieldError}
              hint="Odpowiedź zobaczą tylko pracownicy ROPS. To oni zdecydują, co przekazać mieszkańcowi."
              label="Co radzisz w tej sprawie?"
              multiline
              onChangeText={expert.setBody}
              value={expert.body}
            />
            <PrivacyNote text="Odpowiedź trafi do ROPS w Krakowie." />
            <Trap onChange={expert.setWebsite} value={expert.website} />
            {expert.error ? <Notice tone="error">{expert.error}</Notice> : null}
            {expert.sent ? (
              <Notice
                title="Dziękujemy, odpowiedź trafiła do ROPS"
                tone="success"
              >
                Możesz zamknąć tę stronę albo dopisać kolejną odpowiedź.
              </Notice>
            ) : null}
            <View style={styles.row}>
              <Button
                busy={expert.busy}
                icon={Send}
                label={expert.busy ? "Wysyłam" : "Wyślij odpowiedź"}
                onPress={expert.submit}
                variant="primary"
              />
            </View>
          </Sheet>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  answer: {
    gap: space.xs,
    paddingVertical: space.md,
  },
  group: {
    gap: space.sm,
  },
  row: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
});
