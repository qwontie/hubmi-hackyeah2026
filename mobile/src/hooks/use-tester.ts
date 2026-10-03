import { useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { FeedbackKind, FeedbackSummary, Votes } from "@/api/types";
import type { SelectOption } from "@/lib/options";
import { pluralPl } from "@/lib/plural";
import { useCardVote } from "./use-card-vote";

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
      ? ` ${summary.testers} ${pluralPl(summary.testers, "osoba zgłosiła się", "osoby zgłosiły się", "osób zgłosiło się")} do wolontariatu.`
      : "";
  return `Pasuje: ${summary.fits}. Nie pasuje: ${summary.does_not_fit}.${testers}`;
};

export const useVote = (slug: string, needId?: string, initial?: Votes) => {
  const card = useCardVote(slug, initial, needId);
  const mine: FeedbackKind | null = (() => {
    if (card.mine === "up") {
      return "fits";
    }
    return card.mine === "down" ? "does_not_fit" : null;
  })();
  return {
    busy: (() => {
      if (card.busy === "up") {
        return "fits" as const;
      }
      return card.busy === "down" ? ("does_not_fit" as const) : null;
    })(),
    counts: card.loaded ? { down: card.down, up: card.up } : null,
    error: card.error,
    fromMatch: Boolean(needId),
    line: votesLine(
      card.summary ??
        (card.loaded
          ? {
              does_not_fit: card.down,
              fits: card.up,
              improvements: 0,
              testers: 0,
            }
          : null)
    ),
    mine,
    vote: (kind: FeedbackKind) => card.vote(kind === "fits" ? "up" : "down"),
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
      setError("Uwaga musi mieć co najmniej 10 znaków.");
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
