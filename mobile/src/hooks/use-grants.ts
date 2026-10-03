import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/api/client";
import type { GrantApplication, GrantCall } from "@/api/types";
import { isAbort } from "@/lib/options";
import { getIdea, listIdeas, type StoredIdea } from "@/storage/ideas";
import { useResource } from "./use-resource";

const loadGrantCall = (id: string, signal: AbortSignal) =>
  api.grantCall(id, signal);

export const useGrantCall = (id?: string) => useResource(id, loadGrantCall);

export const useGrantCalls = () => {
  const [calls, setCalls] = useState<GrantCall[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (attempt < 0) {
      return;
    }
    const abort = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      api.grantCalls("open", abort.signal),
      api.grantCalls("upcoming", abort.signal),
    ])
      .then(([open, upcoming]) => {
        const unique = new Map(
          [...open, ...upcoming].map((call) => [call.id, call])
        );
        setCalls([...unique.values()]);
      })
      .catch((caught: unknown) => {
        if (!isAbort(caught)) {
          setError(errorMessage(caught));
        }
      })
      .finally(() => {
        if (!abort.signal.aborted) {
          setLoading(false);
        }
      });
    return () => abort.abort();
  }, [attempt]);

  return {
    calls,
    error,
    loading,
    retry: () => setAttempt((value) => value + 1),
  };
};

export const useApplicationStart = (callId: string) => {
  const [ideas, setIdeas] = useState<StoredIdea[]>([]);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listIdeas()
      .then(setIdeas)
      .catch(() => setIdeas([]));
  }, []);

  const start = async (idea: StoredIdea) => {
    setBusyId(idea.id);
    setError(null);
    try {
      const application = await api.startGrantApplication(
        callId,
        idea.id,
        idea.token
      );
      router.push({
        params: { id: application.id, idea: idea.id },
        pathname: "/nabory/wniosek/[id]",
      });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusyId(null);
    }
  };

  return { busyId, error, ideas, start };
};

export const useGrantApplication = (id?: string, ideaId?: string) => {
  const [application, setApplication] = useState<GrantApplication | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"save" | "submit" | "redraft" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!(id && ideaId)) {
      setLoading(false);
      setError("Brakuje danych wniosku.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const stored = await getIdea(ideaId);
      if (!stored) {
        setError("Nie znaleźliśmy klucza tego pomysłu na tym urządzeniu.");
        return;
      }
      setToken(stored.token);
      const found = await api.grantApplication(id, stored.token);
      setApplication(found);
      setDrafts(
        Object.fromEntries(
          found.sections.map((section) => [section.key, section.text])
        )
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [id, ideaId]);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (
    kind: "save" | "submit" | "redraft",
    action: () => Promise<GrantApplication>
  ) => {
    setBusy(kind);
    setError(null);
    try {
      const next = await action();
      setApplication(next);
      setDrafts(
        Object.fromEntries(
          next.sections.map((section) => [section.key, section.text])
        )
      );
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const save = () => {
    if (id && token) {
      return run("save", () => api.updateGrantApplication(id, token, drafts));
    }
  };
  const redraft = () => {
    if (id && token) {
      return run("redraft", () => api.redraftGrantApplication(id, token));
    }
  };
  const submit = () => {
    if (id && token) {
      return run("submit", () => api.submitGrantApplication(id, token));
    }
  };

  return {
    application,
    busy,
    drafts,
    error,
    loading,
    redraft,
    retry: load,
    save,
    setDraft: (key: string, text: string) =>
      setDrafts((current) => ({ ...current, [key]: text })),
    submit,
  };
};
