import { addEventListener, getInitialURL } from "expo-linking";
import Head from "expo-router/head";
import { useEffect, useRef, useState } from "react";
import { Platform, StyleSheet, type TextInput, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import { APP_NAME } from "@/config";
import { PrivacyNote } from "@/features/privacy-note";
import { EMAIL_INVALID, isEmail } from "@/lib/validation";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox, TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Heading, Txt } from "@/ui/text";

interface Result {
  message: string;
  tone: "error" | "success" | "info";
}

interface Problems {
  consent?: string | null;
  email?: string | null;
}

const emailProblem = (value: string) => {
  if (value.length === 0) {
    return "Wpisz adres e-mail.";
  }
  return isEmail(value) ? null : EMAIL_INVALID;
};

const check = (value: string, consent: boolean): Problems => ({
  consent: consent ? null : "Zaznacz zgodę na wiadomości o naborach.",
  email: emailProblem(value),
});

const linkProblem = (caught: unknown) =>
  caught instanceof ApiError && caught.status >= 400 && caught.status < 500
    ? "Ten link jest nieprawidłowy albo wygasł."
    : errorMessage(caught);

const tokenFromUrl = (url: string) => {
  const fragment = url.split("#", 2)[1] ?? "";
  const params = new URLSearchParams(fragment);
  const confirm = params.get("confirm");
  const unsubscribe = params.get("unsubscribe");
  if (confirm) {
    return { kind: "confirm" as const, token: confirm };
  }
  return unsubscribe
    ? { kind: "unsubscribe" as const, token: unsubscribe }
    : null;
};

export default function GrantNotificationsScreen() {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [problems, setProblems] = useState<Problems>({});
  const field = useRef<TextInput>(null);
  const handled = useRef(new Set<string>());

  useEffect(() => {
    const handle = async (url: string) => {
      const action = tokenFromUrl(url);
      if (!action || handled.current.has(action.token)) {
        return;
      }
      handled.current.add(action.token);
      setBusy(true);
      try {
        if (action.kind === "confirm") {
          await api.confirmGrantSubscription(action.token);
          setResult({
            message: "Adres został potwierdzony. Powiadomimy Cię o naborach.",
            tone: "success",
          });
        } else {
          await api.unsubscribeGrantCalls(action.token);
          setResult({
            message: "Powiadomienia zostały wyłączone.",
            tone: "success",
          });
        }
        if (Platform.OS === "web" && typeof window !== "undefined") {
          window.history.replaceState(
            null,
            "",
            `${window.location.pathname}${window.location.search}`
          );
        }
      } catch (caught) {
        setResult({ message: linkProblem(caught), tone: "error" });
      } finally {
        setBusy(false);
      }
    };
    getInitialURL().then((url) => {
      if (url) {
        return handle(url);
      }
    });
    const subscription = addEventListener("url", ({ url }) => handle(url));
    return () => subscription.remove();
  }, []);

  const subscribe = async () => {
    const value = email.trim();
    const found = check(value, consent);
    setProblems(found);
    if (found.email || found.consent) {
      setResult(null);
      if (found.email) {
        field.current?.focus();
      }
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      await api.subscribeGrantCalls(value);
      setResult({
        message: "Sprawdź pocztę i potwierdź zapis przez link w wiadomości.",
        tone: "success",
      });
    } catch (caught) {
      setResult({ message: errorMessage(caught), tone: "error" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen back="Nabory" width={700}>
      <Head>
        <title>{`Powiadomienia o naborach · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        <Heading level={1}>Powiadomienia o naborach</Heading>
        <Txt tone="soft" variant="lead">
          Wyślemy wiadomość, gdy ruszy nowy nabór lub zmienią się jego terminy.
        </Txt>
        {result ? (
          <Notice
            title={result.tone === "error" ? "Nie udało się" : undefined}
            tone={result.tone}
          >
            {result.message}
          </Notice>
        ) : null}
        <TextField
          autoCapitalize="none"
          autoComplete="email"
          error={problems.email}
          inputMode="email"
          label="Adres e-mail"
          onChangeText={setEmail}
          ref={field}
          value={email}
        />
        <Checkbox
          checked={consent}
          error={problems.consent}
          label="Zgadzam się na wiadomości o naborach. Zapis mogę wyłączyć linkiem w każdej wiadomości."
          onChange={setConsent}
        />
        <PrivacyNote />
        <Button
          busy={busy}
          disabled={busy}
          label="Zapisz mnie"
          onPress={subscribe}
          variant="primary"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({ group: { gap: space.lg } });
