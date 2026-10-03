import { useEffect, useState } from "react";
import { Platform } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { ExpertAnswerView } from "@/api/types";
import { isAbort } from "@/lib/options";
import { pluralPl } from "@/lib/plural";
import { getExpertToken, saveExpertToken } from "@/storage/expert";

const ANSWER_MIN = 10;
const ANSWER_MAX = 5000;
const TOKEN_IN_HASH = /token=([^&]+)/;

const tokenFromLink = () => {
  if (Platform.OS !== "web" || typeof window === "undefined") {
    return null;
  }
  const match = window.location.hash.match(TOKEN_IN_HASH);
  if (!match?.[1]) {
    return null;
  }
  setTimeout(() => {
    window.history.replaceState(
      window.history.state,
      "",
      window.location.pathname + window.location.search
    );
  }, 300);
  return decodeURIComponent(match[1]);
};

type Load =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "error"; message: string }
  | { kind: "ready"; token: string; view: ExpertAnswerView };

const answerProblem = (text: string) => {
  if (text.length < ANSWER_MIN) {
    return `Odpowiedź jest za krótka. Napisz co najmniej ${ANSWER_MIN} znaków.`;
  }
  return text.length > ANSWER_MAX
    ? `Odpowiedź jest za długa. Skróć ją do ${ANSWER_MAX} znaków.`
    : null;
};

const sendFailure = (caught: unknown) => {
  if (!(caught instanceof ApiError)) {
    return errorMessage(caught);
  }
  if (caught.code === "spam_rejected") {
    return "Nie udało się wysłać. Odśwież stronę i spróbuj jeszcze raz.";
  }
  if (caught.code === "rate_limited") {
    const seconds = caught.retryAfter ?? 60;
    return `Za dużo odpowiedzi w krótkim czasie. Spróbuj ponownie za ${seconds} ${pluralPl(seconds, "sekundę", "sekundy", "sekund")}.`;
  }
  if (caught.code === "conflict") {
    return "W tej sprawie zapisaliśmy już 10 odpowiedzi. Jeśli chcesz coś dodać, odpisz na wiadomość od ROPS.";
  }
  return caught.message;
};

export const useExpertAnswer = (id: string | undefined) => {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const [body, setBody] = useState("");
  const [website, setWebsite] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!id) {
      return;
    }
    const abort = new AbortController();
    const open = async () => {
      const fromLink = tokenFromLink();
      if (fromLink) {
        await saveExpertToken(id, fromLink).catch(() => undefined);
      }
      const token = fromLink ?? (await getExpertToken(id));
      if (!token) {
        setLoad({ kind: "missing" });
        return;
      }
      const view = await api.expertAnswers(id, token, abort.signal);
      setLoad({ kind: "ready", token, view });
    };
    open().catch((caught: unknown) => {
      if (isAbort(caught)) {
        return;
      }
      setLoad(
        caught instanceof ApiError && caught.code === "not_found"
          ? { kind: "missing" }
          : { kind: "error", message: errorMessage(caught) }
      );
    });
    return () => abort.abort();
  }, [id]);

  const submit = async () => {
    if (load.kind !== "ready" || !id) {
      return;
    }
    const text = body.trim();
    const problem = answerProblem(text);
    setFieldError(problem);
    setSent(false);
    if (problem) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const view = await api.sendExpertAnswer(id, load.token, {
        body: text,
        ...(website ? { website } : {}),
      });
      setLoad({ kind: "ready", token: load.token, view });
      setBody("");
      setSent(true);
    } catch (caught) {
      setError(sendFailure(caught));
    } finally {
      setBusy(false);
    }
  };

  return {
    body,
    busy,
    error,
    fieldError,
    load,
    sent,
    setBody: (value: string) => {
      setBody(value);
      setFieldError(null);
    },
    setWebsite,
    submit,
    website,
  };
};
