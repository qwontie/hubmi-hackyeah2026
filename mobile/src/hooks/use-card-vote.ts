import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { FeedbackSummary, VoteResponse, Votes } from "@/api/types";
import { getNeed } from "@/storage/needs";
import { getMyVote, type MyVote, setMyVote, voterId } from "@/storage/votes";

const KIND = { down: "does_not_fit", up: "fits" } as const;

const votesFrom = (response: VoteResponse): Votes =>
  response.votes ?? {
    down: response.summary.does_not_fit,
    up: response.summary.fits,
  };

const fromSummary = (summary: FeedbackSummary): Votes => ({
  down: summary.does_not_fit,
  up: summary.fits,
});

export const useCardVote = (slug: string, initial?: Votes, needId?: string) => {
  const [votes, setVotes] = useState<Votes | null>(initial ?? null);
  const [summary, setSummary] = useState<FeedbackSummary | null>(null);
  const [mine, setMine] = useState<MyVote | null>(null);
  const [busy, setBusy] = useState<MyVote | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMyVote(slug)
      .then(setMine)
      .catch(() => setMine(null));
  }, [slug]);

  useEffect(() => {
    if (initial) {
      setVotes(initial);
      return;
    }
    const abort = new AbortController();
    api
      .feedbackSummary(slug, abort.signal)
      .then((result) => {
        setSummary(result);
        setVotes(fromSummary(result));
      })
      .catch(() => setVotes(null));
    return () => abort.abort();
  }, [slug, initial]);

  const vote = useCallback(
    async (kind: MyVote) => {
      setBusy(kind);
      setError(null);
      try {
        const voter = await voterId();
        if (mine === kind) {
          const response = await api.unvote(slug, voter);
          setVotes(votesFrom(response));
          setSummary(response.summary);
          setMine(null);
          await setMyVote(slug, null);
          return;
        }
        const stored = needId ? await getNeed(needId) : null;
        const response = await api.vote(slug, KIND[kind], {
          need: stored ? { id: stored.id, token: stored.token } : undefined,
          voter,
        });
        setVotes(votesFrom(response));
        setSummary(response.summary);
        setMine(kind);
        await setMyVote(slug, kind);
      } catch (caught) {
        setError(errorMessage(caught));
      } finally {
        setBusy(null);
      }
    },
    [slug, mine, needId]
  );

  return {
    busy,
    down: votes?.down ?? 0,
    error,
    loaded: votes !== null,
    mine,
    summary,
    up: votes?.up ?? 0,
    vote,
  };
};
