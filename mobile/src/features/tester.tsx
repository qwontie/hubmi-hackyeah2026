import { Lightbulb, Send, ThumbsDown, ThumbsUp } from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, View } from "react-native";
import { useImprovement, useVote } from "@/hooks/use-tester";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Heading, Txt } from "@/ui/text";

export function VoteBlock({ slug, needId }: { slug: string; needId?: string }) {
  const { busy, error, fromMatch, line, mine, vote } = useVote(slug, needId);
  return (
    <View style={styles.block}>
      <Heading level={2}>
        {fromMatch
          ? "Czy to pasuje do Twojego problemu?"
          : "Czy to rozwiązanie jest przydatne?"}
      </Heading>
      <View style={styles.row}>
        <Button
          busy={busy === "fits"}
          icon={ThumbsUp}
          label="Pasuje"
          onPress={() => vote("fits")}
          pressed={mine === "fits"}
        />
        <Button
          busy={busy === "does_not_fit"}
          icon={ThumbsDown}
          label="Nie pasuje"
          onPress={() => vote("does_not_fit")}
          pressed={mine === "does_not_fit"}
        />
      </View>
      <View aria-live="polite" style={styles.block}>
        {mine ? (
          <Txt tone="ok" weight="500">
            Dziękujemy, zapisaliśmy Twoją ocenę. Możesz ją zmienić.
          </Txt>
        ) : null}
        {line ? (
          <Txt tone="soft" variant="detail">
            {line}
          </Txt>
        ) : null}
        {error ? (
          <Txt tone="bad" weight="500">
            {error}
          </Txt>
        ) : null}
      </View>
    </View>
  );
}

export function ImprovementBlock({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const { busy, done, error, setText, submit, text } = useImprovement(slug);
  return (
    <View style={styles.block}>
      <Heading level={2}>Masz pomysł, jak to ulepszyć?</Heading>
      {done ? (
        <Notice tone="success">
          Dziękujemy. Twoja uwaga trafiła do ROPS. Nie publikujemy jej na
          stronie.
        </Notice>
      ) : null}
      {!done && open ? (
        <>
          <TextField
            error={error}
            hint="Uwagę zobaczą tylko pracownicy ROPS."
            label="Co warto poprawić w tym rozwiązaniu?"
            multiline
            onChangeText={setText}
            value={text}
          />
          <Button
            busy={busy}
            icon={Send}
            label={busy ? "Wysyłam" : "Wyślij uwagę"}
            onPress={submit}
            variant="primary"
          />
        </>
      ) : null}
      {done || open ? null : (
        <Button
          icon={Lightbulb}
          label="Zaproponuj usprawnienie"
          onPress={() => setOpen(true)}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    gap: space.md,
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
});
