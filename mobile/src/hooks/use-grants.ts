import { router } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, errorMessage } from "@/api/client";
import type {
  ApplicationAuth,
  ApplicationPatch,
  ApplicationSection,
  GrantApplication,
  GrantCall,
} from "@/api/types";
import { isAbort } from "@/lib/options";
import { EMAIL_INVALID, isEmail } from "@/lib/validation";
import {
  forgetApplication,
  getApplication,
  listApplications,
  type StoredApplication,
  saveApplication,
  updateApplication,
  useStoredApplications,
} from "@/storage/applications";
import { getIdea, listIdeas, type StoredIdea } from "@/storage/ideas";
import { useResource } from "./use-resource";

const AUTOSAVE_MS = 1500;
const CONSENT_MISSING = "Zaznacz zgodę, żeby ROPS mógł odpisać na ten adres.";

const loadGrantCall = (id: string, signal: AbortSignal) =>
  api.grantCall(id, signal);

const loadGrantCalls = (_attempt: number, signal: AbortSignal) =>
  Promise.all([
    api.grantCalls("open", signal),
    api.grantCalls("upcoming", signal),
  ]);

export const useGrantCall = (id?: string) => useResource(id, loadGrantCall);

export const useGrantCalls = () => {
  const [calls, setCalls] = useState<GrantCall[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError(null);
    loadGrantCalls(attempt, abort.signal)
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

const stateOf = (application: GrantApplication) => ({
  callTitle: application.call.title,
  ideaTitle: application.idea?.title ?? null,
  status: application.status,
  submittedAt: application.submitted_at,
});

export const useMyApplications = () => {
  const stored = useStoredApplications();
  const refreshed = useRef<boolean>(false);

  useEffect(() => {
    if (!stored || refreshed.current) {
      return;
    }
    refreshed.current = true;
    const refresh = async (item: StoredApplication) => {
      try {
        const found = await api.grantApplication(item.id, {
          applicationToken: item.token,
        });
        await updateApplication(item.id, stateOf(found));
      } catch (caught) {
        if (caught instanceof ApiError && caught.code === "not_found") {
          await forgetApplication(item.id);
        }
      }
    };
    for (const item of stored) {
      refresh(item).catch(() => undefined);
    }
  }, [stored]);

  return stored;
};

export const applicationsOfCall = (
  applications: StoredApplication[] | null,
  callId: string
) => (applications ?? []).filter((item) => item.callId === callId);

type CreateState =
  | { kind: "working" }
  | { kind: "choose"; ideas: StoredIdea[] }
  | { kind: "error"; message: string };

export const useApplicationCreate = (callId?: string, ideaId?: string) => {
  const [state, setState] = useState<CreateState>({ kind: "working" });
  const started = useRef<boolean>(false);
  const alive = useRef<boolean>(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const open = useCallback((id: string) => {
    router.replace({ params: { id }, pathname: "/nabory/wniosek/[id]" });
  }, []);

  const create = useCallback(
    async (idea: StoredIdea | null) => {
      if (!callId) {
        return;
      }
      setState({ kind: "working" });
      try {
        const created = await api.createGrantApplication(
          callId,
          { idea_id: idea?.id ?? null },
          idea?.token
        );
        await saveApplication({
          callId,
          createdAt: created.created_at,
          id: created.id,
          ideaId: idea?.id ?? null,
          token: created.edit_token ?? "",
          ...stateOf(created),
        });
        if (alive.current) {
          open(created.id);
        }
      } catch (caught) {
        setState({ kind: "error", message: errorMessage(caught) });
      }
    },
    [callId, open]
  );

  const begin = useCallback(async () => {
    if (!callId) {
      setState({ kind: "error", message: "Brakuje naboru." });
      return;
    }
    const [ideas, applications] = await Promise.all([
      listIdeas(),
      listApplications(),
    ]);
    const mine = applications.filter((item) => item.callId === callId);
    const wanted = ideaId ?? null;
    const existing = mine.find(
      (item) =>
        item.ideaId === wanted && (wanted !== null || item.status === "draft")
    );
    if (existing) {
      open(existing.id);
      return;
    }
    const chosen = ideas.find((idea) => idea.id === wanted);
    if (chosen) {
      await create(chosen);
      return;
    }
    const free = ideas.filter(
      (idea) => !mine.some((item) => item.ideaId === idea.id)
    );
    if (free.length === 0) {
      await create(null);
      return;
    }
    setState({ ideas: free, kind: "choose" });
  }, [callId, create, ideaId, open]);

  useEffect(() => {
    if (started.current) {
      return;
    }
    started.current = true;
    begin().catch((caught: unknown) =>
      setState({ kind: "error", message: errorMessage(caught) })
    );
  }, [begin]);

  return { create, retry: begin, state };
};

export const sameText = (left: string, right: string) =>
  left.trim() === right.trim();

export const isPlaceholder = (section: ApplicationSection, draft: string) =>
  section.source === "ai" &&
  section.missing.length > 0 &&
  sameText(draft, section.text);

const draftsOf = (application: GrantApplication) =>
  Object.fromEntries(
    application.sections.map((section) => [section.key, section.text])
  );

export const useGrantApplication = (id?: string, legacyIdeaId?: string) => {
  const [application, setApplication] = useState<GrantApplication | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [auth, setAuth] = useState<ApplicationAuth | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"submit" | "suggest" | "save" | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempted, setAttempted] = useState(false);
  const [suggested, setSuggested] = useState(false);
  const [justSent, setJustSent] = useState(false);
  const queue = useRef<Promise<void>>(Promise.resolve());

  const accept = useCallback((next: GrantApplication) => {
    setApplication(next);
    updateApplication(next.id, stateOf(next)).catch(() => undefined);
  }, []);

  const load = useCallback(async () => {
    if (!id) {
      setLoading(false);
      setError("Brakuje danych wniosku.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const stored = await getApplication(id);
      const idea = legacyIdeaId ? await getIdea(legacyIdeaId) : null;
      if (!(stored || idea)) {
        setError("Ten wniosek nie jest zapisany na tym urządzeniu.");
        return;
      }
      const found: ApplicationAuth = stored
        ? { applicationToken: stored.token }
        : { ideaToken: idea?.token };
      setAuth(found);
      const next = await api.grantApplication(id, found);
      accept(next);
      setDrafts(draftsOf(next));
      setEmail(next.contact_email ?? "");
      setConsent(next.contact_consent);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [accept, id, legacyIdeaId]);

  useEffect(() => {
    load();
  }, [load]);

  const sections = application?.sections ?? [];
  const editable = application?.status === "draft";
  const changedSections = Object.fromEntries(
    sections
      .filter((section) => !sameText(drafts[section.key] ?? "", section.text))
      .map((section) => [section.key, drafts[section.key] ?? ""])
  );
  const address = email.trim();
  const contactChanged =
    address !== (application?.contact_email ?? "") ||
    (address.length > 0 && consent !== application?.contact_consent);
  const emailError = address.length > 0 && !isEmail(address);
  const consentError = address.length > 0 && !consent;
  const contactValid = !(emailError || consentError);
  const empty = sections
    .filter((section) => {
      const draft = drafts[section.key] ?? "";
      if (!section.required) {
        return false;
      }
      return draft.trim().length === 0 || isPlaceholder(section, draft);
    })
    .map((section) => section.key);
  const tooLong = sections
    .filter(
      (section) => (drafts[section.key] ?? "").length > section.max_length
    )
    .map((section) => section.key);

  const patch = (): ApplicationPatch | null => {
    if (!editable) {
      return null;
    }
    const body: ApplicationPatch = {};
    const fitting = Object.fromEntries(
      Object.entries(changedSections).filter(([key]) => !tooLong.includes(key))
    );
    if (Object.keys(fitting).length > 0) {
      body.sections = fitting;
    }
    if (contactChanged && contactValid) {
      if (address) {
        body.contact_consent = true;
        body.contact_email = address;
      } else {
        body.contact_consent = false;
      }
    }
    return Object.keys(body).length > 0 ? body : null;
  };
  const patchRef = useRef(patch);
  patchRef.current = patch;
  const pending = patch();
  const patchKey = pending ? JSON.stringify(pending) : "";

  const save = useCallback(() => {
    const next = queue.current
      .catch(() => undefined)
      .then(async () => {
        const body = patchRef.current();
        if (!(id && auth && body)) {
          return;
        }
        accept(await api.updateGrantApplication(id, auth, body));
        setSavedAt(new Date());
      });
    queue.current = next;
    return next;
  }, [accept, auth, id]);

  const saveRef = useRef(save);
  saveRef.current = save;

  useEffect(() => {
    if (busy || patchKey === "") {
      return;
    }
    const timer = setTimeout(() => {
      saveRef.current().catch((caught: unknown) => {
        setError(errorMessage(caught));
      });
    }, AUTOSAVE_MS);
    return () => clearTimeout(timer);
  }, [busy, patchKey]);

  useEffect(
    () => () => {
      saveRef.current().catch(() => undefined);
    },
    []
  );

  const run = async (
    kind: "submit" | "suggest",
    action: () => Promise<void>
  ) => {
    setBusy(kind);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const saveNow = async () => {
    setBusy("save");
    setError(null);
    try {
      await save();
      setSavedAt(new Date());
      return true;
    } catch (caught) {
      setError(errorMessage(caught));
      return false;
    } finally {
      setBusy(null);
    }
  };

  const suggest = () => {
    if (!(id && auth)) {
      return;
    }
    return run("suggest", async () => {
      await save();
      const next = await api.suggestGrantApplication(id, auth);
      accept(next);
      setDrafts(draftsOf(next));
      setSuggested(true);
    });
  };

  const submit = () => {
    if (!(id && auth)) {
      return;
    }
    setAttempted(true);
    if (empty.length > 0 || tooLong.length > 0 || !contactValid) {
      setError(null);
      return;
    }
    return run("submit", async () => {
      await save();
      const next = await api.submitGrantApplication(id, auth);
      accept(next);
      setDrafts(draftsOf(next));
      setJustSent(true);
    });
  };

  return {
    application,
    attempted,
    busy,
    consent,
    consentError: attempted && consentError ? CONSENT_MISSING : null,
    drafts,
    editable,
    email,
    emailError: attempted && emailError ? EMAIL_INVALID : null,
    empty,
    error,
    justSent,
    loading,
    retry: load,
    savedAt,
    saveNow,
    setConsent,
    setDraft: (key: string, text: string) =>
      setDrafts((current) => ({ ...current, [key]: text })),
    setEmail,
    submit,
    suggest,
    suggested,
    tooLong,
    unsaved: patchKey !== "",
  };
};
