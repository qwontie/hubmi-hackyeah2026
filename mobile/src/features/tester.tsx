import {
  FlaskConical,
  Lightbulb,
  Send,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react-native";
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type {
  FeedbackKind,
  FeedbackSummary,
  Powiat,
  TesterRole,
} from "@/api/types";
import { pluralPl } from "@/lib/plural";
import { getNeed } from "@/storage/needs";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Select } from "@/ui/select";
import { Heading, Txt } from "@/ui/text";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const ROLES: { value: TesterRole; label: string }[] = [
  { label: "Mieszkaniec lub mieszkanka", value: "resident" },
  { label: "Organizacja pozarządowa", value: "ngo" },
  { label: "Samorząd lub jednostka samorządu", value: "local_government" },
  { label: "Ekspert lub ekspertka", value: "expert" },
];

const votesLine = (summary: FeedbackSummary) => {
  const total = summary.fits + summary.does_not_fit;
  if (total === 0) {
    return null;
  }
  return `Oceny: ${summary.fits} pasuje, ${summary.does_not_fit} nie pasuje. ${
    summary.testers > 0
      ? `${summary.testers} ${pluralPl(summary.testers, "osoba chce", "osoby chcą", "osób chce")} testować.`
      : ""
  }`.trim();
};

export function VoteBlock({ slug, needId }: { slug: string; needId?: string }) {
  const [summary, setSummary] = useState<FeedbackSummary | null>(null);
  const [mine, setMine] = useState<FeedbackKind | null>(null);
  const [busy, setBusy] = useState<FeedbackKind | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    api
      .feedbackSummary(slug, abort.signal)
      .then(setSummary)
      .catch(() => setSummary(null));
    return () => abort.abort();
  }, [slug]);

  const vote = async (kind: FeedbackKind) => {
    setBusy(kind);
    setError(null);
    try {
      const stored = needId ? await getNeed(needId) : null;
      const response = await api.vote(
        slug,
        kind,
        stored ? { id: stored.id, token: stored.token } : undefined
      );
      setMine(kind);
      setSummary(response.summary);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const line = summary ? votesLine(summary) : null;

  return (
    <View style={styles.block}>
      <Heading level={2}>
        {needId
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

interface SignupErrors {
  consent: string | null;
  email: string | null;
}

const validateSignup = (email: string, consent: boolean): SignupErrors => ({
  consent: consent
    ? null
    : "Zaznacz zgodę, żeby ROPS mógł się z Tobą skontaktować.",
  email: EMAIL.test(email)
    ? null
    : "Wpisz pełny adres e-mail, np. jan@poczta.pl.",
});

function SignupForm({
  slug,
  onDone,
}: {
  slug: string;
  onDone: (email: string) => void;
}) {
  const [powiats, setPowiats] = useState<Powiat[]>([]);
  useEffect(() => {
    const abort = new AbortController();
    api
      .powiats(abort.signal)
      .then(setPowiats)
      .catch(() => setPowiats([]));
    return () => abort.abort();
  }, []);
  const [who, setWho] = useState<TesterRole>("resident");
  const [organization, setOrganization] = useState("");
  const [powiat, setPowiat] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<SignupErrors>({
    consent: null,
    email: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const trimmed = email.trim();
    const problems = validateSignup(trimmed, consent);
    setErrors(problems);
    if (problems.email || problems.consent) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.testSignup(slug, {
        contact_consent: true,
        contact_email: trimmed,
        who,
        ...(organization.trim() ? { organization: organization.trim() } : {}),
        ...(powiat ? { powiat } : {}),
        ...(note.trim() ? { note: note.trim() } : {}),
      });
      onDone(trimmed);
    } catch (caught) {
      const fields = caught instanceof ApiError ? caught.fields : [];
      const fieldMessage = (name: string) =>
        fields.find((field) => field.field === name)?.message ?? null;
      setErrors({
        consent: fieldMessage("contact_consent"),
        email: fieldMessage("contact_email"),
      });
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.block}>
      <Select
        label="Kim jesteś?"
        onChange={(value) => setWho(value as TesterRole)}
        options={ROLES}
        value={who}
      />
      {who === "resident" ? null : (
        <TextField
          label="Nazwa organizacji lub instytucji"
          onChangeText={setOrganization}
          value={organization}
        />
      )}
      {powiats.length > 0 ? (
        <Select
          emptyLabel="Nie wybieram"
          label="Powiat"
          onChange={setPowiat}
          optional
          options={powiats.map((item) => ({
            label: item.name,
            value: item.slug,
          }))}
          value={powiat}
        />
      ) : null}
      <TextField
        autoCapitalize="none"
        autoComplete="email"
        error={errors.email}
        hint="ROPS napisze na ten adres, gdy ruszą testy."
        inputMode="email"
        keyboardType="email-address"
        label="Twój adres e-mail"
        onChangeText={setEmail}
        textContentType="emailAddress"
        value={email}
      />
      <TextField
        label="Dodatkowe informacje (nieobowiązkowo)"
        multiline
        onChangeText={setNote}
        value={note}
      />
      <Checkbox
        checked={consent}
        error={errors.consent}
        label="Zgadzam się, żeby ROPS w Krakowie użył mojego adresu e-mail do kontaktu w sprawie testów tej innowacji."
        onChange={setConsent}
      />
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button
        busy={busy}
        icon={Send}
        label={busy ? "Wysyłam…" : "Zgłoś się do testów"}
        onPress={submit}
        variant="primary"
      />
    </View>
  );
}

export function TestSignupBlock({ slug }: { slug: string }) {
  const [open, setOpen] = useState(false);
  const [doneEmail, setDoneEmail] = useState<string | null>(null);
  return (
    <View style={styles.block}>
      <Heading level={2}>Chcesz przetestować to rozwiązanie?</Heading>
      {doneEmail ? (
        <Notice title="Jesteś na liście testujących" tone="success">
          {`ROPS napisze na adres ${doneEmail}, gdy ruszą testy.`}
        </Notice>
      ) : null}
      {!doneEmail && open ? (
        <SignupForm onDone={setDoneEmail} slug={slug} />
      ) : null}
      {doneEmail || open ? null : (
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
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async () => {
    const trimmed = text.trim();
    if (trimmed.length < 10) {
      setError("Opisz pomysł w co najmniej 10 znakach.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.improve(slug, trimmed);
      setDone(true);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

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
