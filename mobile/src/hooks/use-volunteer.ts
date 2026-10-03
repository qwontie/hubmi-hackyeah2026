import { useCallback, useEffect, useState } from "react";
import { Platform } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type {
  ErrorCode,
  InnovationSummary,
  TesterRole,
  VolunteerRecommend,
  VolunteerView,
} from "@/api/types";
import { isAbort } from "@/lib/options";
import { pluralPl } from "@/lib/plural";
import { EMAIL_INVALID, fieldMessage, isEmail } from "@/lib/validation";
import { getVolunteerToken, saveVolunteerToken } from "@/storage/volunteers";
import { usePagedList } from "./use-paged-list";

const PROPOSAL_MIN = 20;
const PROPOSAL_MAX = 2000;
const REPORT_MAX = 4000;
const WORDS = /\s+/;
const TOKEN_IN_HASH = /token=([^&]+)/;
const POWIAT_MISSING = "Wybierz powiat.";
const CONSENT_MISSING = "Zaznacz zgodę, żeby ROPS mógł napisać na ten adres.";
const SPAM_REJECTED =
  "Nie udało się wysłać. Odśwież stronę i spróbuj jeszcze raz.";

const PROPOSAL_MESSAGES: Partial<Record<ErrorCode, string>> = {
  text_too_long: `Opis jest za długi. Skróć go do ${PROPOSAL_MAX} znaków.`,
  text_too_short: `Opis jest za krótki. Napisz co najmniej ${PROPOSAL_MIN} znaków.`,
  too_few_words: "Napisz co najmniej dwa słowa o tym, co chcesz zrobić.",
  too_many_links: "W opisie mogą być najwyżej dwa linki. Usuń pozostałe.",
};

const proposalProblem = (text: string) => {
  if (text.length < PROPOSAL_MIN) {
    return PROPOSAL_MESSAGES.text_too_short ?? null;
  }
  if (text.length > PROPOSAL_MAX) {
    return PROPOSAL_MESSAGES.text_too_long ?? null;
  }
  return text.split(WORDS).length < 2
    ? (PROPOSAL_MESSAGES.too_few_words ?? null)
    : null;
};

const sendFailure = (caught: unknown) => {
  if (!(caught instanceof ApiError)) {
    return errorMessage(caught);
  }
  if (caught.code === "spam_rejected") {
    return SPAM_REJECTED;
  }
  if (caught.code === "rate_limited") {
    const seconds = caught.retryAfter ?? 60;
    return `Za dużo zgłoszeń w krótkim czasie. Spróbuj ponownie za ${seconds} ${pluralPl(seconds, "sekundę", "sekundy", "sekund")}.`;
  }
  if (PROPOSAL_MESSAGES[caught.code] || caught.code === "validation_error") {
    return null;
  }
  return caught.message;
};

interface VolunteerErrors {
  consent: string | null;
  email: string | null;
  powiat: string | null;
  proposal: string | null;
}

const noVolunteerErrors: VolunteerErrors = {
  consent: null,
  email: null,
  powiat: null,
  proposal: null,
};

const PAGE_SIZE = 12;

export const useVolunteerSolutions = () => {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const load = useCallback(
    (page: number, signal: AbortSignal) =>
      api.innovations(
        {
          page,
          per_page: PAGE_SIZE,
          q: query.length >= 2 ? query : undefined,
        },
        signal
      ),
    [query]
  );
  const paged = usePagedList<InnovationSummary>(`volunteer:${query}`, load);
  return {
    ...paged,
    clear: () => {
      setDraft("");
      setQuery("");
    },
    draft,
    query,
    search: () => setQuery(draft.trim()),
    setDraft,
  };
};

export const useVolunteer = (slug: string, startOpen = false) => {
  const [open, setOpen] = useState(startOpen);
  const [who, setWho] = useState<TesterRole>("resident");
  const [organization, setOrganization] = useState("");
  const [powiat, setPowiat] = useState("");
  const [proposal, setProposal] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState("");
  const [errors, setErrors] = useState<VolunteerErrors>(noVolunteerErrors);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{
    duplicate: boolean;
    email: string;
  } | null>(null);

  const submit = async () => {
    const address = email.trim();
    const text = proposal.trim().split(WORDS).join(" ");
    const problems: VolunteerErrors = {
      consent: consent ? null : CONSENT_MISSING,
      email: isEmail(address) ? null : EMAIL_INVALID,
      powiat: powiat ? null : POWIAT_MISSING,
      proposal: proposalProblem(text),
    };
    setErrors(problems);
    if (Object.values(problems).some(Boolean)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await api.volunteer(slug, {
        contact_consent: true,
        email: address,
        powiat,
        proposal: text,
        who,
        ...(organization.trim() ? { organization: organization.trim() } : {}),
        ...(website ? { website } : {}),
      });
      setDone({ duplicate: result.duplicate, email: address });
    } catch (caught) {
      setErrors({
        consent: fieldMessage(caught, "contact_consent"),
        email: fieldMessage(caught, "email"),
        powiat: fieldMessage(caught, "powiat"),
        proposal:
          caught instanceof ApiError
            ? (PROPOSAL_MESSAGES[caught.code] ?? null)
            : null,
      });
      setError(sendFailure(caught));
    } finally {
      setBusy(false);
    }
  };

  return {
    busy,
    consent,
    done,
    email,
    error,
    errors,
    needsOrganization: who !== "resident",
    open,
    organization,
    powiat,
    proposal,
    setConsent,
    setEmail,
    setOpen,
    setOrganization,
    setPowiat: (value: string) => {
      setPowiat(value);
      setErrors((current) => ({ ...current, powiat: null }));
    },
    setProposal: (value: string) => {
      setProposal(value);
      setErrors((current) => ({ ...current, proposal: null }));
    },
    setWebsite,
    setWho,
    submit,
    website,
    who,
  };
};

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

type ReportLoad =
  | { kind: "loading" }
  | { kind: "missing" }
  | { kind: "error"; message: string }
  | { kind: "ready"; token: string; view: VolunteerView };

interface ReportErrors {
  activity: string | null;
  notWorked: string | null;
  participants: string | null;
  recommend: string | null;
  worked: string | null;
}

const noReportErrors: ReportErrors = {
  activity: null,
  notWorked: null,
  participants: null,
  recommend: null,
  worked: null,
};

const DIGITS = /^\d{1,6}$/;

const lengthProblem = (text: string, min: number) => {
  if (text.length < min) {
    return `Napisz co najmniej ${min} ${pluralPl(min, "znak", "znaki", "znaków")}.`;
  }
  return text.length > REPORT_MAX
    ? `Tekst jest za długi. Skróć go do ${REPORT_MAX} znaków.`
    : null;
};

export const useVolunteerReport = (id: string | undefined) => {
  const [load, setLoad] = useState<ReportLoad>({ kind: "loading" });
  const [activity, setActivity] = useState("");
  const [participants, setParticipants] = useState("");
  const [worked, setWorked] = useState("");
  const [notWorked, setNotWorked] = useState("");
  const [recommend, setRecommend] = useState<VolunteerRecommend | null>(null);
  const [errors, setErrors] = useState<ReportErrors>(noReportErrors);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!id) {
      return;
    }
    const abort = new AbortController();
    const open = async () => {
      const fromLink = tokenFromLink();
      if (fromLink) {
        await saveVolunteerToken(id, fromLink).catch(() => undefined);
      }
      const token = fromLink ?? (await getVolunteerToken(id));
      if (!token) {
        setLoad({ kind: "missing" });
        return;
      }
      const view = await api.volunteerView(id, token, abort.signal);
      if (view.report) {
        setActivity(view.report.activity);
        setParticipants(String(view.report.participants));
        setWorked(view.report.worked);
        setNotWorked(view.report.not_worked);
        setRecommend(view.report.recommend);
      }
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
    const count = participants.trim();
    const problems: ReportErrors = {
      activity: lengthProblem(activity.trim(), 10),
      notWorked: lengthProblem(notWorked.trim(), 2),
      participants: DIGITS.test(count)
        ? null
        : "Wpisz liczbę osób, na przykład 12. Jeśli nikt nie brał udziału, wpisz 0.",
      recommend: recommend ? null : "Wybierz jedną odpowiedź.",
      worked: lengthProblem(worked.trim(), 2),
    };
    setErrors(problems);
    setSaved(false);
    if (Object.values(problems).some(Boolean) || !recommend) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const view = await api.volunteerReport(id, load.token, {
        activity: activity.trim(),
        not_worked: notWorked.trim(),
        participants: Number.parseInt(count, 10),
        recommend,
        worked: worked.trim(),
      });
      setLoad({ kind: "ready", token: load.token, view });
      setSaved(true);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return {
    activity,
    busy,
    error,
    errors,
    load,
    notWorked,
    participants,
    recommend,
    saved,
    setActivity,
    setNotWorked,
    setParticipants,
    setRecommend,
    setWorked,
    submit,
    worked,
  };
};
