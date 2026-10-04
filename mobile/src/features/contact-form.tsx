import { Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { PrivacyNote } from "@/features/privacy-note";
import { useContactForm } from "@/hooks/use-contact";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";

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
  const {
    busy,
    consent,
    consentError,
    email,
    emailError,
    error,
    needsConsent,
    setConsent,
    setEmail,
    submit,
  } = useContactForm({ needId, nothingFits, onDone, requireEmail, token });

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
      {needsConsent ? (
        <Checkbox
          checked={consent}
          error={consentError}
          label="Zgadzam się, żeby ROPS w Krakowie użył tego adresu tylko do odpowiedzi na moje zgłoszenie."
          onChange={setConsent}
        />
      ) : null}
      <PrivacyNote />
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button
        busy={busy}
        icon={Send}
        label={busy ? "Wysyłam" : submitLabel}
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
