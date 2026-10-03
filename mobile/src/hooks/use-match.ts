import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Text, TextInput } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { MatchResponse } from "@/api/types";
import { TEXT_MAX, TEXT_MIN } from "@/config";
import { focusAndAnnounce } from "@/lib/a11y";
import { isAbort } from "@/lib/options";
import { pluralPl } from "@/lib/plural";
import { useRecognition } from "@/speech/recognition";
import { saveNeed } from "@/storage/needs";

export type MatchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; response: MatchResponse; at: Date }
  | { kind: "error"; message: string; retryable: boolean };

const FIELD_ERRORS = new Set([
  "text_too_short",
  "text_too_long",
  "unclear_text",
  "validation_error",
]);

export const resultsTitle = (count: number) => {
  if (count === 0) {
    return "Nie znaleźliśmy gotowego rozwiązania";
  }
  return `Znaleźliśmy ${count} ${pluralPl(
    count,
    "gotowe rozwiązanie",
    "gotowe rozwiązania",
    "gotowych rozwiązań"
  )}`;
};

export const similarSentence = (count: number) => {
  if (count === 0) {
    return "Jesteś pierwszą osobą, która opisała taki problem. Twoje zgłoszenie już trafiło do ROPS.";
  }
  return `${pluralPl(count, "osoba", "osoby", "osób")} z Małopolski ${pluralPl(
    count,
    "zgłosiła",
    "zgłosiły",
    "zgłosiło"
  )} podobny problem. Twoje zgłoszenie trafiło do ROPS.`;
};

export const matchSpeech = (response: MatchResponse) => {
  const parts = [
    `${resultsTitle(response.results.length)}.`,
    response.similar_count > 0
      ? `${response.similar_count} ${similarSentence(response.similar_count)}`
      : similarSentence(0),
  ];
  response.results.forEach((result, index) => {
    parts.push(
      `Propozycja ${index + 1}: ${result.innovation.title}. ${result.reason}`
    );
  });
  return parts.join(" ");
};

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

export const charactersLeft = (length: number) => {
  const remaining = TEXT_MAX - length;
  if (remaining >= 200) {
    return null;
  }
  return {
    over: remaining < 0,
    text:
      remaining < 0
        ? `Za długo o ${-remaining} znaków.`
        : `Zostało ${remaining} znaków.`,
  };
};

export const useMatch = () => {
  const params = useLocalSearchParams<{ powiat?: string }>();
  const [text, setTextState] = useState("");
  const [powiat, setPowiat] = useState(params.powiat ?? "");

  useEffect(() => {
    if (params.powiat) {
      setPowiat(params.powiat);
    }
  }, [params.powiat]);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [state, setState] = useState<MatchState>({ kind: "idle" });
  const [blockedUntil, setBlockedUntil] = useState(0);
  const inputRef = useRef<TextInput>(null);
  const resultsRef = useRef<Text>(null);
  const controller = useRef<AbortController | null>(null);

  const appendSpoken = useCallback((spoken: string) => {
    setTextState((current) => {
      const base = current.trimEnd();
      return base.length > 0 ? `${base} ${spoken}` : spoken;
    });
    setFieldError(null);
  }, []);

  const recognition = useRecognition(appendSpoken);

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
      focusAndAnnounce(
        resultsRef.current,
        resultsTitle(state.response.results.length)
      );
    }
  }, [state]);

  useEffect(() => () => controller.current?.abort(), []);

  const setText = (value: string) => {
    setTextState(value);
    setFieldError(null);
  };

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
      if (!isAbort(caught)) {
        fail(caught);
      }
    }
  };

  const reset = () => {
    controller.current?.abort();
    setTextState("");
    setPowiat("");
    setState({ kind: "idle" });
    setFieldError(null);
    inputRef.current?.focus();
  };

  return {
    blocked: blockedUntil > 0,
    fieldError,
    inputRef,
    loading: state.kind === "loading",
    powiat,
    recognition,
    reset,
    resultsRef,
    setPowiat,
    setText,
    state,
    submit,
    text,
  };
};
