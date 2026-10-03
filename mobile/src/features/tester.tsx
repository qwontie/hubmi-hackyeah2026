import {
  FlaskConical,
  Lightbulb,
  Send,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, View } from "react-native";
import { usePowiats } from "@/hooks/use-powiats";
import {
  TESTER_ROLES,
  useImprovement,
  useTestSignup,
  useVote,
} from "@/hooks/use-tester";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Select } from "@/ui/select";
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

function SignupForm({ signup }: { signup: ReturnType<typeof useTestSignup> }) {
  const powiats = usePowiats();
  return (
    <View style={styles.block}>
      <Select
        label="Kim jesteś?"
        onChange={signup.setWho}
        options={TESTER_ROLES}
        value={signup.who}
      />
      {signup.needsOrganization ? (
        <TextField
          label="Nazwa organizacji lub instytucji"
          onChangeText={signup.setOrganization}
          value={signup.organization}
        />
      ) : null}
      {powiats.options.length > 0 ? (
        <Select
          emptyLabel="Nie wybieram"
          label="Powiat"
          onChange={signup.setPowiat}
          optional
          options={powiats.options}
          value={signup.powiat}
        />
      ) : null}
      <TextField
        autoCapitalize="none"
        autoComplete="email"
        error={signup.errors.email}
        hint="ROPS napisze na ten adres, gdy ruszą testy."
        inputMode="email"
        keyboardType="email-address"
        label="Twój adres e-mail"
        onChangeText={signup.setEmail}
        textContentType="emailAddress"
        value={signup.email}
      />
      <TextField
        label="Dodatkowe informacje (nieobowiązkowo)"
        multiline
        onChangeText={signup.setNote}
        value={signup.note}
      />
      <Checkbox
        checked={signup.consent}
        error={signup.errors.consent}
        label="Zgadzam się, żeby ROPS w Krakowie użył mojego adresu e-mail do kontaktu w sprawie testów tej innowacji."
        onChange={signup.setConsent}
      />
      {signup.error ? <Notice tone="error">{signup.error}</Notice> : null}
      <Button
        busy={signup.busy}
        icon={Send}
        label={signup.busy ? "Wysyłam…" : "Zgłoś się do testów"}
        onPress={signup.submit}
        variant="primary"
      />
    </View>
  );
}

export function TestSignupBlock({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const signup = useTestSignup(slug);
  return (
    <View style={styles.block}>
      <Heading level={2}>Chcesz przetestować to rozwiązanie?</Heading>
      {signup.doneEmail ? (
        <Notice title="Jesteś na liście testujących" tone="success">
          {`ROPS napisze na adres ${signup.doneEmail}, gdy ruszą testy.`}
        </Notice>
      ) : null}
      {!signup.doneEmail && open ? <SignupForm signup={signup} /> : null}
      {signup.doneEmail || open ? null : (
        <Button
          icon={FlaskConical}
          label="Chcę testować"
          onPress={() => setOpen(true)}
        />
      )}
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
          Dziękujemy. Twój pomysł trafił do ROPS. Nie publikujemy go na stronie.
        </Notice>
      ) : null}
      {!done && open ? (
        <>
          <TextField
            error={error}
            hint="Pomysł zobaczą tylko pracownicy ROPS."
            label="Twój pomysł na usprawnienie"
            multiline
            onChangeText={setText}
            value={text}
          />
          <Button
            busy={busy}
            icon={Send}
            label={busy ? "Wysyłam…" : "Wyślij pomysł"}
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
