import { RotateCcw, Search } from "lucide-react-native";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  findNodeHandle,
  Platform,
  StyleSheet,
  type Text,
  type TextInput,
  View,
} from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { MatchResponse, Powiat } from "@/api/types";
import { TEXT_MAX, TEXT_MIN } from "@/config";
import { MatchResults, resultsTitle } from "@/features/match-results";
import { VoiceInput } from "@/features/voice-input";
import { pluralPl } from "@/lib/plural";
import { useRecognition } from "@/speech/recognition";
import { saveNeed } from "@/storage/needs";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Select } from "@/ui/select";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";
import { focusElement } from "@/ui/web-globals";

type State =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; response: MatchResponse; at: Date }
  | { kind: "error"; message: string; retryable: boolean };

const TITLE_ID = "problem-title";

const FIELD_ERRORS = new Set([
  "text_too_short",
  "text_too_long",
  "unclear_text",
  "validation_error",
]);

const validate = (text: string) => {
  const { length } = text.trim();
  if (length < TEXT_MIN) {
    return `Opisz problem w co najmniej ${TEXT_MIN} znakach. Jedno lub dwa zdania wystarczą.`;
  }
  if (length > TEXT_MAX) {
    return `Opis jest za długi. Skróć go do ${TEXT_MAX} znaków.`;
  }
  return null;
};

const rateLimitMessage = (error: ApiError) => {
  const seconds = error.retryAfter ?? 60;
  return `${error.message} Możesz spróbować ponownie za ${seconds} ${pluralPl(
    seconds,
    "sekundę",
    "sekundy",
    "sekund"
  )}.`;
};

const announceResults = (node: Text | null, count: number) => {
  if (Platform.OS === "web") {
    focusElement(node);
    return;
  }
  const handle = node ? findNodeHandle(node) : null;
  if (handle) {
    AccessibilityInfo.setAccessibilityFocus(handle);
  }
  AccessibilityInfo.announceForAccessibility(resultsTitle(count));
};

function CharactersLeft({ length }: { length: number }) {
  const remaining = TEXT_MAX - length;
  if (remaining >= 200) {
    return null;
  }
  return (
    <Txt
      aria-live="polite"
      tone={remaining < 0 ? "bad" : "soft"}
      variant="small"
    >
      {remaining < 0
        ? `Za długo o ${-remaining} znaków.`
        : `Zostało ${remaining} znaków.`}
    </Txt>
  );
}

export default function MatchScreen() {
  const { wide } = useTheme();
  const [text, setText] = useState("");
  const [powiat, setPowiat] = useState("");
  const [powiats, setPowiats] = useState<Powiat[]>([]);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [state, setState] = useState<State>({ kind: "idle" });
  const [blockedUntil, setBlockedUntil] = useState(0);
  const inputRef = useRef<TextInput>(null);
  const resultsRef = useRef<Text>(null);
  const controller = useRef<AbortController | null>(null);

  const appendSpoken = useCallback((spoken: string) => {
    setText((current) => {
      const base = current.trimEnd();
      return base.length > 0 ? `${base} ${spoken}` : spoken;
    });
    setFieldError(null);
  }, []);

  const recognition = useRecognition(appendSpoken);

  useEffect(() => {
    const abort = new AbortController();
    api
      .powiats(abort.signal)
      .then(setPowiats)
      .catch(() => setPowiats([]));
    return () => abort.abort();
  }, []);

  useEffect(() => {
    if (blockedUntil === 0) {
      return;
    }
    const timer = setTimeout(
      () => setBlockedUntil(0),
      Math.max(blockedUntil - Date.now(), 0)
    );
    return () => clearTimeout(timer);
  }, [blockedUntil]);

  useEffect(() => {
    if (state.kind === "done") {
      announceResults(resultsRef.current, state.response.results.length);
    }
  }, [state]);

  useEffect(() => () => controller.current?.abort(), []);

  const fail = (caught: unknown) => {
    if (caught instanceof ApiError && FIELD_ERRORS.has(caught.code)) {
      setState({ kind: "idle" });
      setFieldError(
        caught.fields.find((field) => field.field === "text")?.message ??
          caught.message
      );
      inputRef.current?.focus();
      return;
    }
    if (caught instanceof ApiError && caught.code === "rate_limited") {
      setBlockedUntil(Date.now() + (caught.retryAfter ?? 60) * 1000);
      setState({
        kind: "error",
        message: rateLimitMessage(caught),
        retryable: false,
      });
      return;
    }
    setState({ kind: "error", message: errorMessage(caught), retryable: true });
  };

  const submit = async () => {
    recognition.stop();
    const problem = validate(text);
    setFieldError(problem);
    if (problem) {
      inputRef.current?.focus();
      return;
    }
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setState({ kind: "loading" });
    const trimmed = text.trim();
    try {
      const response = await api.match(
        { text: trimmed, ...(powiat ? { powiat } : {}) },
        abort.signal
      );
      const at = new Date();
      await saveNeed({
        clusterTitle: response.cluster?.title ?? null,
        contactEmail: null,
        createdAt: at.toISOString(),
        id: response.need.id,
        nothingFits: false,
        number: response.need.number ?? null,
        text: trimmed,
        token: response.need.edit_token,
      }).catch(() => undefined);
      setState({ at, kind: "done", response });
    } catch (caught) {
      if (!(caught instanceof Error && caught.name === "AbortError")) {
        fail(caught);
      }
    }
  };

  const reset = () => {
    controller.current?.abort();
    setText("");
    setPowiat("");
    setState({ kind: "idle" });
    setFieldError(null);
    inputRef.current?.focus();
  };

  const loading = state.kind === "loading";

  return (
    <Screen>
      <Sheet raised>
        <View style={styles.intro}>
          <Heading level={1} nativeID={TITLE_ID}>
            Opisz problem
          </Heading>
          <Txt tone="soft" variant="lead">
            Napisz zwykłymi słowami, z czym potrzebujesz pomocy. Pokażemy
            sprawdzone rozwiązania z biblioteki innowacji ROPS w Krakowie.
          </Txt>
        </View>

        <View style={styles.field}>
          <TextField
            error={fieldError}
            label="Opisz problem"
            labelledBy={TITLE_ID}
            large
            maxLength={TEXT_MAX + 200}
            multiline
            onChangeText={(value) => {
              setText(value);
              setFieldError(null);
            }}
            placeholder="Na przykład: mama ma demencję, wychodzi z domu i się gubi."
            ref={inputRef}
            value={text}
          />
          <CharactersLeft length={text.length} />
        </View>

        <VoiceInput recognition={recognition} />

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

        <View style={[styles.actions, wide && styles.actionsWide]}>
          <Button
            busy={loading}
            disabled={blockedUntil > 0}
            fill={!wide}
            icon={Search}
            label={loading ? "Szukam rozwiązań…" : "Znajdź rozwiązania"}
            onPress={submit}
            size="large"
            variant="primary"
          />
          {state.kind === "done" ? (
            <Button
              icon={RotateCcw}
              label="Opisz inny problem"
              onPress={reset}
              variant="quiet"
            />
          ) : null}
        </View>

        <View aria-live="polite">
          {loading ? (
            <Txt tone="soft">
              Szukamy w bibliotece ROPS. To trwa zwykle kilka sekund.
            </Txt>
          ) : null}
        </View>
      </Sheet>

      {state.kind === "error" ? (
        <Notice tone="error">
          <View style={styles.errorBody}>
            <Txt>{state.message}</Txt>
            {state.retryable ? (
              <Button label="Spróbuj ponownie" onPress={submit} />
            ) : null}
          </View>
        </Notice>
      ) : null}

      {state.kind === "done" ? (
        <MatchResults
          at={state.at}
          key={state.response.need.id}
          response={state.response}
          titleRef={resultsRef}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: {
    gap: space.md,
  },
  actionsWide: {
    alignItems: "center",
    flexDirection: "row",
  },
  errorBody: {
    gap: space.md,
  },
  field: {
    gap: space.sm,
  },
  intro: {
    gap: space.md,
  },
});
