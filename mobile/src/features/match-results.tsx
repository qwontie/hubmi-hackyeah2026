import { Link } from "expo-router";
import { type Ref, useState } from "react";
import { StyleSheet, type Text, View } from "react-native";
import type { MatchResponse } from "@/api/types";
import { ContactForm } from "@/features/contact-form";
import { InnovationRow } from "@/features/innovation-row";
import { ReadAloudButton } from "@/features/read-aloud-button";
import { Stamp } from "@/features/stamp";
import { matchSpeech, resultsTitle, similarSentence } from "@/hooks/use-match";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

function NothingFits({
  response,
  empty,
}: {
  response: MatchResponse;
  empty: boolean;
}) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(empty);
  const [done, setDone] = useState<{ email: string | null } | null>(null);

  if (done) {
    return (
      <Notice title="Przekazaliśmy to do ROPS" tone="success">
        <Txt>
          {done.email
            ? `Pracownik ROPS przeczyta Twój opis i odpisze na adres ${done.email}.`
            : "Pracownik ROPS przeczyta Twój opis. Jeśli chcesz dostać odpowiedź, dodaj e-mail w zakładce Moje zgłoszenia."}
        </Txt>
        <Link href="/zgloszenia" style={{ color: colors.stamp }}>
          <Txt tone="stamp" weight="600">
            Przejdź do Moich zgłoszeń
          </Txt>
        </Link>
      </Notice>
    );
  }

  return (
    <>
      <Heading level={3}>
        {empty ? "Przekaż problem do ROPS" : "Nic z tego nie pasuje?"}
      </Heading>
      <Txt>
        Daj znać pracownikom ROPS. Zostaw e-mail, jeśli chcesz, żeby ktoś
        odpisał.
      </Txt>
      {open ? (
        <ContactForm
          needId={response.need.id}
          nothingFits
          onDone={(email) => setDone({ email })}
          submitLabel="Wyślij do ROPS"
          token={response.need.edit_token}
        />
      ) : (
        <Button label="Nic nie pasuje" onPress={() => setOpen(true)} />
      )}
    </>
  );
}

interface MatchResultsProps {
  at: Date;
  response: MatchResponse;
  titleRef: Ref<Text>;
}

export function MatchResults({ response, at, titleRef }: MatchResultsProps) {
  const { colors, type, wide } = useTheme();
  const count = response.results.length;
  const empty = count === 0;
  return (
    <Sheet>
      <View style={[styles.summary, wide && styles.summaryWide]}>
        <View style={styles.summaryText}>
          <Heading level={2} ref={titleRef}>
            {resultsTitle(count)}
          </Heading>
          <View style={styles.similar}>
            {response.similar_count > 0 ? (
              <Txt
                mono
                style={{
                  fontSize: type.h1,
                  lineHeight: Math.round(type.h1 * 1.1),
                }}
                tone="stamp"
              >
                {response.similar_count}
              </Txt>
            ) : null}
            <Txt style={styles.similarText} variant="lead">
              {similarSentence(response.similar_count)}
            </Txt>
          </View>
          {response.cluster ? (
            <Txt tone="soft" variant="detail">
              Temat: {response.cluster.title}
            </Txt>
          ) : null}
        </View>
        <Stamp at={at} number={response.need.number} word="PRZYJĘTO" />
      </View>

      {empty ? null : <ReadAloudButton text={matchSpeech(response)} />}

      {response.degraded ? (
        <Txt tone="soft" variant="detail">
          Asystent jest teraz przeciążony, więc opisy dopasowania są
          uproszczone. Same propozycje pochodzą z biblioteki ROPS.
        </Txt>
      ) : null}

      {empty ? null : (
        <View role="list">
          {response.results.map((result, index) => (
            <InnovationRow
              index={index + 1}
              innovation={result.innovation}
              key={result.innovation.slug}
              last={index === count - 1}
              needId={response.need.id}
              reason={result.reason}
            />
          ))}
        </View>
      )}

      <View
        style={[
          styles.nothing,
          { borderTopColor: colors.rule },
          empty && styles.nothingFirst,
        ]}
      >
        <NothingFits empty={empty} response={response} />
      </View>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  nothing: {
    borderTopWidth: 1,
    gap: space.md,
    paddingTop: space.xl,
  },
  nothingFirst: {
    borderTopWidth: 0,
    paddingTop: 0,
  },
  similar: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
  },
  similarText: {
    flex: 1,
  },
  summary: {
    gap: space.lg,
  },
  summaryText: {
    flex: 1,
    gap: space.md,
  },
  summaryWide: {
    alignItems: "flex-start",
    flexDirection: "row",
    justifyContent: "space-between",
  },
});
