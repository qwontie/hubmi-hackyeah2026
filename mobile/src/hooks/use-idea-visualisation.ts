import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { AuthorIdea } from "@/api/types";
import { getIdea } from "@/storage/ideas";

export const useIdeaVisualisation = (id?: string) => {
  const [idea, setIdea] = useState<AuthorIdea | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const stored = await getIdea(id);
      if (!stored) {
        setError("Ten pomysł nie jest zapisany na tym urządzeniu.");
        return;
      }
      setToken(stored.token);
      setIdea(await api.idea(id, stored.token));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const generate = async () => {
    if (!(id && token) || generating) {
      return;
    }
    setGenerating(true);
    setError(null);
    try {
      const result = await api.ideaVisualisation(id, token);
      setIdea((current) =>
        current
          ? {
              ...current,
              visualisation_alt: result.alt,
              visualisation_url: result.url,
              visualisations_left: result.generations_left,
            }
          : current
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setGenerating(false);
    }
  };

  return { error, generate, generating, idea, loading, retry: load };
};
