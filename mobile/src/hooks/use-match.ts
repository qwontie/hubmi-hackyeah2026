import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Text, TextInput } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { ClusterRef, MatchResponse, NeedCreate } from "@/api/types";
import { TEXT_MAX, TEXT_MIN } from "@/config";
import { focusAndAnnounce } from "@/lib/a11y";
import { isAbort } from "@/lib/options";
import { pluralPl } from "@/lib/plural";
import { EMAIL_INVALID, isEmail } from "@/lib/validation";
import { useRecognition } from "@/speech/recognition";
import { saveNeed } from "@/storage/needs";

export type MatchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "done"; response: MatchResponse; at: Date; query: string }
  | { kind: "error"; message: string; retryable: boolean };

export interface RegisteredNeed {
  at: Date;
  cluster: ClusterRef | null;
  edit_token: string;
  id: string;
  number: number | null;
  similar_count: number;
}

export interface RegistrationInput {
  contactConsent?: boolean;
  contactEmail?: string;
  powiat?: string;
}

interface RegistrationErrors {
  consent: string | null;
  email: string | null;
  powiat: string | null;
}

export interface RegistrationForm {
  consent: boolean;
  email: string;
  errors: RegistrationErrors;
  open: boolean;
  powiat: string;
  setConsent: (value: boolean) => void;
  setEmail: (value: string) => void;
  setOpen: (value: boolean) => void;
  setPowiat: (value: string) => void;
  submit: () => Promise<void>;
}

const emptyRegistrationErrors: RegistrationErrors = {
  consent: null,
  email: null,
  powiat: null,
};

const validateRegistration = (
  email: string,
  consent: boolean
): RegistrationErrors => ({
  consent:
    email && !consent
      ? "Zaznacz zgodę, żeby ROPS mógł odpisać na ten adres."
      : null,
  email: email && !isEmail(email) ? EMAIL_INVALID : null,
  powiat: null,
});

const registrationErrorsFrom = (caught: unknown): RegistrationErrors | null => {
  if (!(caught instanceof ApiError)) {
    return null;
  }
  const fields = Object.fromEntries(
    caught.fields.map((field) => [field.field, field.message])
  );
  return {
    consent: fields.contact_consent ?? null,
    email: fields.contact_email ?? null,
    powiat: fields.powiat ?? null,
  };
};

const needRequest = (
  response: MatchResponse,
  text: string,
  powiat: string,
  email: string,
  consent: boolean
): NeedCreate => ({
  shown_innovation_slugs: response.results.map(
    (result) => result.innovation.slug
  ),
  text,
  ...(powiat ? { powiat } : {}),
  ...(email ? { contact_consent: consent, contact_email: email } : {}),
});

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
    return "Nie mamy jeszcze podobnego zgłoszenia z Małopolski.";
  }
  return `${pluralPl(count, "osoba", "osoby", "osób")} z Małopolski ${pluralPl(
    count,
    "zgłosiła",
    "zgłosiły",
    "zgłosiło"
  )} podobny problem.`;
};

export const matchSpeech = (response: MatchResponse) => {
  const parts = [
    `${resultsTitle(response.results.length)}.`,
    similarSentence(response.similar_count),
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
  const [registeredNeed, setRegisteredNeed] = useState<RegisteredNeed | null>(
    null
  );
  const [registering, setRegistering] = useState(false);
  const [registrationError, setRegistrationError] = useState<string | null>(
    null
  );
  const [registrationErrors, setRegistrationErrors] =
    useState<RegistrationErrors>(emptyRegistrationErrors);
  const [registrationOpen, setRegistrationOpen] = useState(false);
  const [registrationPowiat, setRegistrationPowiat] = useState(powiat);
  const [registrationEmail, setRegistrationEmail] = useState("");
  const [registrationConsent, setRegistrationConsent] = useState(false);
  const registeringRef = useRef(false);
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
      setRegisteredNeed(null);
      setRegistrationPowiat(powiat);
      setState({ at, kind: "done", query: trimmed, response });
    } catch (caught) {
      if (!isAbort(caught)) {
        fail(caught);
      }
    }
  };

  const register = async (input: RegistrationInput = {}) => {
    if (state.kind !== "done" || registeredNeed || registeringRef.current) {
      return;
    }
    const contactConsent = input.contactConsent ?? registrationConsent;
    const email = (input.contactEmail ?? registrationEmail).trim();
    const selectedPowiat = input.powiat ?? registrationPowiat;
    const errors = validateRegistration(email, contactConsent);
    setRegistrationErrors(errors);
    if (errors.consent || errors.email) {
      return;
    }
    registeringRef.current = true;
    setRegistering(true);
    setRegistrationError(null);
    try {
      const created = await api.createNeed(
        needRequest(
          state.response,
          state.query,
          selectedPowiat,
          email,
          contactConsent
        )
      );
      const registered = { ...created, at: new Date() };
      await saveNeed({
        clusterTitle: created.cluster?.title ?? null,
        contactEmail: email || null,
        createdAt: registered.at.toISOString(),
        id: created.id,
        nothingFits: true,
        number: created.number,
        text: state.query,
        token: created.edit_token,
      }).catch(() => undefined);
      setRegisteredNeed(registered);
    } catch (caught) {
      const errorsFromApi = registrationErrorsFrom(caught);
      if (errorsFromApi) {
        setRegistrationErrors(errorsFromApi);
      }
      setRegistrationError(errorMessage(caught));
    } finally {
      registeringRef.current = false;
      setRegistering(false);
    }
  };

  const reset = () => {
    controller.current?.abort();
    setTextState("");
    setPowiat("");
    setState({ kind: "idle" });
    setRegisteredNeed(null);
    setRegistrationError(null);
    setRegistrationErrors(emptyRegistrationErrors);
    setRegistrationOpen(false);
    setRegistrationPowiat("");
    setRegistrationEmail("");
    setRegistrationConsent(false);
    setFieldError(null);
    inputRef.current?.focus();
  };

  const registrationFields: RegistrationForm = {
    consent: registrationConsent,
    email: registrationEmail,
    errors: registrationErrors,
    open: registrationOpen,
    powiat: registrationPowiat,
    setConsent: (value) => {
      setRegistrationConsent(value);
      setRegistrationErrors((current) => ({ ...current, consent: null }));
    },
    setEmail: (value) => {
      setRegistrationEmail(value);
      setRegistrationErrors((current) => ({
        ...current,
        consent: value.trim() ? current.consent : null,
        email: null,
      }));
    },
    setOpen: setRegistrationOpen,
    setPowiat: (value) => {
      setRegistrationPowiat(value);
      setRegistrationErrors((current) => ({ ...current, powiat: null }));
    },
    submit: () => register(),
  };

  return {
    blocked: blockedUntil > 0,
    fieldError,
    inputRef,
    loading: state.kind === "loading",
    powiat,
    recognition,
    register,
    registeredNeed,
    registering,
    registrationError,
    registrationFields,
    reset,
    resultsRef,
    setPowiat,
    setText,
    state,
    submit,
    text,
  };
};
