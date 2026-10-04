import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { BookOpen, Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { VolunteerRecommend, VolunteerReport } from "@/api/types";
import { APP_NAME } from "@/config";
import { PrivacyNote } from "@/features/privacy-note";
import { ChoiceGrid } from "@/features/volunteer";
import { useVolunteerReport } from "@/hooks/use-volunteer";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const RECOMMEND: { label: string; value: VolunteerRecommend }[] = [
  { label: "Tak", value: "yes" },
  { label: "Tak, po zmianach", value: "after_changes" },
  { label: "Nie", value: "no" },
];

const CLOSED_WORDS: Record<string, string> = {
  closed: "ROPS zamknął to zgłoszenie. Raportu nie można już zmienić.",
  new: "Pracownik ROPS jeszcze nie odpowiedział na Twoje zgłoszenie. Raport będzie można wpisać, gdy je przyjmie.",
  rejected: "ROPS nie przyjął tego zgłoszenia, więc raportu się nie wpisuje.",
};

function Form({ report }: { report: ReturnType<typeof useVolunteerReport> }) {
  return (
    <Sheet>
      <Heading level={2}>Raport z działania</Heading>
      <TextField
        error={report.errors.activity}
        hint="Co udało się zrobić, gdzie i z kim."
        label="Co zrobiłeś lub zrobiłaś?"
        multiline
        onChangeText={report.setActivity}
        value={report.activity}
      />
      <TextField
        error={report.errors.participants}
        hint="Sama liczba, na przykład 12."
        inputMode="numeric"
        keyboardType="number-pad"
        label="Ile osób wzięło udział?"
        onChangeText={report.setParticipants}
        value={report.participants}
      />
      <TextField
        error={report.errors.worked}
        label="Co zadziałało?"
        multiline
        onChangeText={report.setWorked}
        rows={3}
        value={report.worked}
      />
      <TextField
        error={report.errors.notWorked}
        hint="Także to, co warto zmienić."
        label="Co nie zadziałało?"
        multiline
        onChangeText={report.setNotWorked}
        rows={3}
        value={report.notWorked}
      />
      <ChoiceGrid
        error={report.errors.recommend}
        label="Czy polecasz to rozwiązanie innym?"
        onChange={(value) => report.setRecommend(value as VolunteerRecommend)}
        options={RECOMMEND}
        value={report.recommend}
      />
      <PrivacyNote text="Raport trafi do ROPS w Krakowie." />
      {report.error ? <Notice tone="error">{report.error}</Notice> : null}
      {report.saved ? (
        <Notice title="Zapisaliśmy raport" tone="success">
          ROPS go zobaczy. Możesz go jeszcze poprawić i zapisać ponownie.
        </Notice>
      ) : null}
      <View style={styles.row}>
        <Button
          busy={report.busy}
          icon={Send}
          label={report.busy ? "Zapisuję" : "Zapisz raport"}
          onPress={report.submit}
          variant="primary"
        />
      </View>
    </Sheet>
  );
}

function Sent({ report }: { report: VolunteerReport }) {
  const { colors } = useTheme();
  const answers = [
    ["Co zrobiłeś lub zrobiłaś?", report.activity],
    ["Ile osób wzięło udział?", String(report.participants)],
    ["Co zadziałało?", report.worked],
    ["Co nie zadziałało?", report.not_worked],
    [
      "Czy polecasz to rozwiązanie innym?",
      RECOMMEND.find((option) => option.value === report.recommend)?.label ??
        "",
    ],
  ];
  return (
    <Sheet>
      <Heading level={2}>Twój raport</Heading>
      <View role="list">
        {answers.map(([question, answer], index) => (
          <View
            key={question}
            role="listitem"
            style={[
              styles.answer,
              { borderTopColor: colors.rule },
              index === 0 && styles.first,
            ]}
          >
            <Txt weight="600">{question}</Txt>
            <Txt>{answer}</Txt>
          </View>
        ))}
      </View>
    </Sheet>
  );
}

export default function VolunteerReportScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const report = useVolunteerReport(id);
  const { load } = report;
  return (
    <Screen back="Działaj" backFallback="/dzialaj" title="Raport wolontariusza">
      <Head>
        <title>{`Raport wolontariusza · ${APP_NAME}`}</title>
      </Head>

      {load.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję zgłoszenie.
        </Txt>
      ) : null}

      {load.kind === "missing" ? (
        <Notice title="Ten link nie działa" tone="error">
          <View style={styles.group}>
            <Txt>
              Otwórz stronę linkiem z wiadomości e-mail od ROPS. Jeśli link
              nadal nie działa, odpisz na tę wiadomość.
            </Txt>
            <Button
              icon={BookOpen}
              label="Przejdź do biblioteki"
              onPress={() => router.replace("/biblioteka")}
            />
          </View>
        </Notice>
      ) : null}

      {load.kind === "error" ? (
        <Notice title="Nie udało się wczytać zgłoszenia" tone="error">
          {load.message}
        </Notice>
      ) : null}

      {load.kind === "ready" ? (
        <>
          <Sheet raised>
            <View style={styles.group}>
              <Txt tone="soft" variant="label">
                {`Rozwiązanie · ${load.view.powiat_name}`}
              </Txt>
              <Heading level={2}>{load.view.innovation.title}</Heading>
            </View>
            <View style={styles.group}>
              <Txt variant="label" weight="600">
                Twoje zgłoszenie
              </Txt>
              <Txt>{load.view.proposal}</Txt>
            </View>
          </Sheet>
          {load.view.editable ? (
            <Form report={report} />
          ) : (
            <>
              <Notice tone="info">
                {CLOSED_WORDS[load.view.status] ?? CLOSED_WORDS.closed}
              </Notice>
              {load.view.report ? <Sent report={load.view.report} /> : null}
            </>
          )}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  answer: {
    borderTopWidth: 1,
    gap: space.xs,
    paddingVertical: space.md,
  },
  first: {
    borderTopWidth: 0,
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
