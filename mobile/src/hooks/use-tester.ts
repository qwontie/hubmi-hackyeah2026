import { useEffect, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { FeedbackKind, FeedbackSummary, TesterRole } from "@/api/types";
import type { SelectOption } from "@/lib/options";
import { pluralPl } from "@/lib/plural";
import { EMAIL_INVALID, fieldMessage, isEmail } from "@/lib/validation";
import { getNeed } from "@/storage/needs";

export const TESTER_ROLES: SelectOption[] = [
  { label: "Mieszkaniec lub mieszkanka", value: "resident" },
  { label: "Organizacja pozarządowa", value: "ngo" },
  { label: "Samorząd lub jednostka samorządu", value: "local_government" },
  { label: "Ekspert lub ekspertka", value: "expert" },
];

export const votesLine = (summary: FeedbackSummary | null) => {
  if (!summary || summary.fits + summary.does_not_fit === 0) {
    return null;
  }
  const testers =
    summary.testers > 0
      ? ` ${summary.testers} ${pluralPl(summary.testers, "osoba chce", "osoby chcą", "osób chce")} testować.`
      : "";
  return `Oceny: ${summary.fits} pasuje, ${summary.does_not_fit} nie pasuje.${testers}`;
};

export const useVote = (slug: string, needId?: string) => {
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

  return {
    busy,
    error,
    fromMatch: Boolean(needId),
    line: votesLine(summary),
    mine,
    vote,
  };
};

interface SignupErrors {
  consent: string | null;
  email: string | null;
}

export const useTestSignup = (slug: string) => {
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
  const [doneEmail, setDoneEmail] = useState<string | null>(null);

  const submit = async () => {
    const trimmed = email.trim();
    const problems = {
      consent: consent
        ? null
        : "Zaznacz zgodę, żeby ROPS mógł się z Tobą skontaktować.",
      email: isEmail(trimmed) ? null : EMAIL_INVALID,
    };
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
      setDoneEmail(trimmed);
    } catch (caught) {
      setErrors({
        consent: fieldMessage(caught, "contact_consent"),
        email: fieldMessage(caught, "contact_email"),
      });
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return {
    busy,
    consent,
    doneEmail,
    email,
    error,
    errors,
    needsOrganization: who !== "resident",
    note,
    organization,
    powiat,
    setConsent,
    setEmail,
    setNote,
    setOrganization,
    setPowiat,
    setWho: (value: string) => setWho(value as TesterRole),
    submit,
    who,
  };
};

export const useImprovement = (slug: string) => {
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

  return { busy, done, error, setText, submit, text };
};
