import { Send } from "lucide-react-native";
import { useState } from "react";
import { StyleSheet, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import { updateNeed } from "@/storage/needs";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const validateContact = (
  email: string,
  consent: boolean,
  requireEmail: boolean
) => {
  const problems: { email: string | null; consent: string | null } = {
    consent: null,
    email: null,
  };
  if (email.length === 0) {
    if (requireEmail) {
      problems.email = "Wpisz adres e-mail, na który ROPS ma odpisać.";
    }
    return problems;
  }
  if (!EMAIL.test(email)) {
    problems.email =
      "Ten adres wygląda na niepełny. Sprawdź go, np. jan@poczta.pl.";
  }
  if (!consent) {
    problems.consent = "Zaznacz zgodę, żeby ROPS mógł odpisać na ten adres.";
  }
  return problems;
};

interface ContactFormProps {
  needId: string;
  nothingFits: boolean;
  onDone: (email: string | null) => void;
  requireEmail?: boolean;
  submitLabel: string;
  token: string;
}

export function ContactForm({
  needId,
  token,
  nothingFits,
  submitLabel,
  requireEmail = false,
  onDone,
}: ContactFormProps) {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [consentError, setConsentError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    const trimmed = email.trim();
    const problems = validateContact(trimmed, consent, requireEmail);
    setEmailError(problems.email);
    setConsentError(problems.consent);
    if (problems.email || problems.consent) {
      return;
    }
    const hasEmail = trimmed.length > 0;
    setBusy(true);
    setError(null);
    try {
      await api.patchNeed(needId, token, {
        ...(nothingFits ? { nothing_fits: true } : {}),
        ...(hasEmail ? { contact_consent: true, contact_email: trimmed } : {}),
      });
      await updateNeed(needId, {
        ...(nothingFits ? { nothingFits: true } : {}),
        ...(hasEmail ? { contactEmail: trimmed } : {}),
      });
      onDone(hasEmail ? trimmed : null);
    } catch (caught) {
      const fields = caught instanceof ApiError ? caught.fields : [];
      const fieldMessage = (name: string) =>
        fields.find((field) => field.field === name)?.message ?? null;
      setEmailError(fieldMessage("contact_email"));
      setConsentError(fieldMessage("contact_consent"));
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.form}>
      <TextField
        autoCapitalize="none"
        autoComplete="email"
        error={emailError}
        hint={
          requireEmail
            ? "Odpowiedź przyjdzie na ten adres."
            : "Nieobowiązkowo. Podaj, jeśli chcesz dostać odpowiedź."
        }
        inputMode="email"
        keyboardType="email-address"
        label="Twój adres e-mail"
        onChangeText={setEmail}
        onSubmitEditing={submit}
        textContentType="emailAddress"
        value={email}
      />
      {email.trim().length > 0 ? (
        <Checkbox
          checked={consent}
          error={consentError}
          label="Zgadzam się, żeby ROPS w Krakowie użył tego adresu tylko do odpowiedzi na moje zgłoszenie."
          onChange={setConsent}
        />
      ) : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button
        busy={busy}
        icon={Send}
        label={busy ? "Wysyłam…" : submitLabel}
        onPress={submit}
        variant="primary"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  form: {
    gap: space.lg,
  },
});
