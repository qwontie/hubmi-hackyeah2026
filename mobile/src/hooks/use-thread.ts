import { useCallback, useEffect, useState } from "react";
import { Platform } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { ThreadMessage } from "@/api/types";
import { TEXT_MAX } from "@/config";
import { formatDate } from "@/lib/plural";
import { getIdea, saveIdea, updateIdea } from "@/storage/ideas";
import { getNeed, saveNeed, updateNeed } from "@/storage/needs";

const REFRESH_MS = 30_000;
const TOKEN_IN_HASH = /token=([^&]+)/;

export type ThreadKind = "need" | "idea";

export interface ThreadView {
  canEmail: boolean;
  closed: boolean;
  code: string | null;
  createdAt: string;
  id: string;
  messages: ThreadMessage[];
  statusLabel: string;
  text: string;
  waiting: boolean;
}

export type ThreadLoad =
  | { kind: "loading" }
  | { kind: "no-token" }
  | { kind: "error"; message: string }
  | { kind: "done"; thread: ThreadView; token: string };

const NEED_STATUS = {
  answered: "ROPS odpowiedział",
  closed: "Sprawa zamknięta",
  new: "Czeka na odpowiedź ROPS",
} as const;

const IDEA_STATUS = {
  accepted: "Pomysł przyjęty przez ROPS",
  in_review: "ROPS czyta pomysł",
  new: "Czeka na ROPS",
  rejected: "ROPS nie przyjął pomysłu",
} as const;

export const numberCode = (value: number | null | undefined) =>
  value ? `HUB/${String(value).padStart(4, "0")}` : null;

export const messageTime = (iso: string) => {
  const date = new Date(iso);
  return `${formatDate(iso)}, godz. ${date.toLocaleTimeString("pl-PL", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
};

const linkToken = () => {
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

const resolveToken = async (kind: ThreadKind, id: string) => {
  const fromLink = linkToken();
  const stored = kind === "need" ? await getNeed(id) : await getIdea(id);
  if (fromLink && !stored) {
    const createdAt = new Date().toISOString();
    if (kind === "need") {
      await saveNeed({
        clusterTitle: null,
        contactEmail: null,
        createdAt,
        id,
        nothingFits: false,
        number: null,
        text: "",
        token: fromLink,
      });
    } else {
      await saveIdea({
        createdAt,
        id,
        number: null,
        title: "",
        token: fromLink,
      });
    }
  }
  return fromLink ?? stored?.token ?? null;
};

const fetchView = async (
  kind: ThreadKind,
  id: string,
  token: string
): Promise<ThreadView> => {
  if (kind === "need") {
    const thread = await api.thread(id, token);
    await updateNeed(id, {
      number: thread.need.number,
      text: thread.need.text,
    });
    return {
      canEmail: thread.can_email,
      closed: thread.need.status === "closed",
      code: numberCode(thread.need.number),
      createdAt: thread.need.created_at,
      id,
      messages: thread.messages,
      statusLabel: NEED_STATUS[thread.need.status],
      text: thread.need.text,
      waiting: thread.need.status === "new",
    };
  }
  const thread = await api.ideaThread(id, token);
  await updateIdea(id, {
    number: thread.idea.number,
    title: thread.idea.title,
  });
  return {
    canEmail: thread.can_email,
    closed: thread.idea.status === "rejected",
    code: numberCode(thread.idea.number),
    createdAt: thread.idea.created_at,
    id,
    messages: thread.messages,
    statusLabel: IDEA_STATUS[thread.idea.status],
    text: thread.idea.title,
    waiting: thread.idea.status === "new",
  };
};

export const useThread = (kind: ThreadKind, id: string | undefined) => {
  const [load, setLoad] = useState<ThreadLoad>({ kind: "loading" });

  const refresh = useCallback(
    async (quiet: boolean) => {
      if (!id) {
        return;
      }
      const token = await resolveToken(kind, id);
      if (!token) {
        setLoad({ kind: "no-token" });
        return;
      }
      try {
        const thread = await fetchView(kind, id, token);
        setLoad({ kind: "done", thread, token });
      } catch (caught) {
        if (quiet) {
          return;
        }
        if (caught instanceof ApiError && caught.code === "not_found") {
          setLoad({ kind: "no-token" });
          return;
        }
        setLoad({ kind: "error", message: errorMessage(caught) });
      }
    },
    [kind, id]
  );

  useEffect(() => {
    refresh(false);
    const timer = setInterval(() => refresh(true), REFRESH_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  const append = (message: ThreadMessage) =>
    setLoad((current) =>
      current.kind === "done"
        ? {
            ...current,
            thread: {
              ...current.thread,
              messages: [...current.thread.messages, message],
              waiting: true,
            },
          }
        : current
    );

  return { append, load, refresh };
};

export const useReply = (
  kind: ThreadKind,
  id: string,
  token: string,
  onSent: (message: ThreadMessage) => void
) => {
  const [body, setBodyState] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sentAt, setSentAt] = useState<Date | null>(null);

  const setBody = (value: string) => {
    setBodyState(value);
    setSentAt(null);
  };

  const send = async () => {
    const trimmed = body.trim();
    if (trimmed.length === 0) {
      setError("Napisz wiadomość, zanim ją wyślesz.");
      return;
    }
    if (trimmed.length > TEXT_MAX) {
      setError(`Wiadomość jest za długa. Skróć ją do ${TEXT_MAX} znaków.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const message =
        kind === "need"
          ? await api.sendMessage(id, token, trimmed)
          : await api.sendIdeaMessage(id, token, trimmed);
      setBodyState("");
      setSentAt(new Date(message.sent_at));
      onSent(message);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return { body, busy, error, send, sentAt, setBody };
};
