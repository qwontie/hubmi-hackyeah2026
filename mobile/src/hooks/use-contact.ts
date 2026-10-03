import { useState } from "react";
import { api, errorMessage } from "@/api/client";
import { EMAIL_INVALID, fieldMessage, isEmail } from "@/lib/validation";
import { updateNeed } from "@/storage/needs";

interface ContactOptions {
  needId: string;
  nothingFits: boolean;
  onDone: (email: string | null) => void;
  requireEmail: boolean;
  token: string;
}

const validateContact = (
  email: string,
  consent: boolean,
  requireEmail: boolean
) => {
  if (email.length === 0) {
    return {
      consent: null,
      email: requireEmail
        ? "Wpisz adres e-mail, na który ROPS ma odpisać."
        : null,
    };
  }
  return {
    consent: consent
      ? null
      : "Zaznacz zgodę, żeby ROPS mógł odpisać na ten adres.",
    email: isEmail(email) ? null : EMAIL_INVALID,
  };
};

export const useContactForm = ({
  needId,
  token,
  nothingFits,
  requireEmail,
  onDone,
}: ContactOptions) => {
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
      setEmailError(fieldMessage(caught, "contact_email"));
      setConsentError(fieldMessage(caught, "contact_consent"));
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return {
    busy,
    consent,
    consentError,
    email,
    emailError,
    error,
    needsConsent: email.trim().length > 0,
    setConsent,
    setEmail,
    submit,
  };
};
