import { useEffect, useState } from "react";
import { ApiError, api, errorMessage } from "@/api/client";
import { pluralPl } from "@/lib/plural";
import { EMAIL_INVALID, fieldMessage, isEmail } from "@/lib/validation";

const POWIAT_MISSING = "Wybierz powiat.";
const CONSENT_MISSING = "Zaznacz zgodę, żeby ROPS mógł napisać na ten adres.";
const SPAM_REJECTED =
  "Nie udało się wysłać. Odśwież stronę i spróbuj jeszcze raz.";

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
  return caught.code === "validation_error" ? null : caught.message;
};

export const demandWords = (count: number) =>
  `${count} ${pluralPl(count, "osoba chce", "osoby chcą", "osób chce")} tego rozwiązania u siebie.`;

interface DemandErrors {
  consent: string | null;
  email: string | null;
  powiat: string | null;
}

const noDemandErrors: DemandErrors = {
  consent: null,
  email: null,
  powiat: null,
};

export const useDemand = (slug: string) => {
  const [count, setCount] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const [powiat, setPowiat] = useState("");
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [website, setWebsite] = useState("");
  const [errors, setErrors] = useState<DemandErrors>(noDemandErrors);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ duplicate: boolean } | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    api
      .demandCount(slug, abort.signal)
      .then((result) => setCount(result.count))
      .catch(() => undefined);
    return () => abort.abort();
  }, [slug]);

  const submit = async () => {
    const address = email.trim();
    const problems: DemandErrors = {
      consent: address && !consent ? CONSENT_MISSING : null,
      email: address && !isEmail(address) ? EMAIL_INVALID : null,
      powiat: powiat ? null : POWIAT_MISSING,
    };
    setErrors(problems);
    if (problems.consent || problems.email || problems.powiat) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await api.demand(slug, {
        contact_consent: Boolean(address) && consent,
        powiat,
        ...(address ? { email: address } : {}),
        ...(website ? { website } : {}),
      });
      setCount(result.count);
      setDone({ duplicate: result.duplicate });
    } catch (caught) {
      setErrors({
        consent: fieldMessage(caught, "contact_consent"),
        email: fieldMessage(caught, "email"),
        powiat: fieldMessage(caught, "powiat"),
      });
      setError(sendFailure(caught));
    } finally {
      setBusy(false);
    }
  };

  return {
    busy,
    consent,
    count,
    done,
    email,
    error,
    errors,
    open,
    powiat,
    setConsent,
    setEmail,
    setOpen,
    setPowiat: (value: string) => {
      setPowiat(value);
      setErrors((current) => ({ ...current, powiat: null }));
    },
    setWebsite,
    submit,
    website,
  };
};
