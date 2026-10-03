import { router, useLocalSearchParams } from "expo-router";
import Head from "expo-router/head";
import { ArrowLeft, Send } from "lucide-react-native";
import { useCallback, useEffect, useState } from "react";
import { Platform, StyleSheet, View } from "react-native";
import { ApiError, api, errorMessage } from "@/api/client";
import type { NeedThread, ThreadMessage } from "@/api/types";
import { APP_NAME, TEXT_MAX } from "@/config";
import { ContactForm } from "@/features/contact-form";
import { Stamp } from "@/features/stamp";
import { formatDate } from "@/lib/plural";
import { getNeed, saveNeed, updateNeed } from "@/storage/needs";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const REFRESH_MS = 30_000;
const TOKEN_IN_HASH = /token=([^&]+)/;

type Load =
  | { kind: "loading" }
  | { kind: "no-token" }
  | { kind: "missing" }
  | { kind: "error"; message: string }
  | { kind: "done"; thread: NeedThread; token: string };

const STATUS: Record<NeedThread["need"]["status"], string> = {
  answered: "ROPS odpowiedział",
  closed: "Sprawa zamknięta",
  new: "Czeka na odpowiedź ROPS",
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

const resolveToken = async (id: string) => {
  const fromLink = linkToken();
  const stored = await getNeed(id);
  if (fromLink && !stored) {
    await saveNeed({
      clusterTitle: null,
      contactEmail: null,
      createdAt: new Date().toISOString(),
      id,
      nothingFits: false,
      number: null,
      text: "",
      token: fromLink,
    });
  }
  return fromLink ?? stored?.token ?? null;
};

const numberCode = (value: number | null) =>
  value ? `HUB/${String(value).padStart(4, "0")}` : null;

const timeLabel = (iso: string) => {
  const date = new Date(iso);
  return `${formatDate(iso)}, godz. ${date.toLocaleTimeString("pl-PL", {
    hour: "2-digit",
    minute: "2-digit",
  })}`;
};

function Message({ message }: { message: ThreadMessage }) {
  const { colors, borderWidth } = useTheme();
  const fromRops = message.direction === "to_author";
  return (
    <View
      role="listitem"
      style={[
        styles.message,
        {
          backgroundColor: fromRops ? colors.paper : colors.sunk,
          borderColor: fromRops ? colors.rule : colors.sunk,
          borderWidth,
          marginLeft: fromRops ? 0 : space.xl,
          marginRight: fromRops ? space.xl : 0,
        },
      ]}
    >
      <Txt tone="soft" variant="detail">
        <Txt
          tone={fromRops ? "stamp" : "default"}
          variant="detail"
          weight="600"
        >
          {fromRops ? "ROPS w Krakowie" : "Ty"}
        </Txt>
        {` · ${timeLabel(message.sent_at)}`}
      </Txt>
      <Txt>{message.body}</Txt>
    </View>
  );
}

function Reply({
  id,
  token,
  onSent,
}: {
  id: string;
  token: string;
  onSent: (message: ThreadMessage) => void;
}) {
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sentAt, setSentAt] = useState<Date | null>(null);

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
      const message = await api.sendMessage(id, token, trimmed);
      setBody("");
      setSentAt(new Date(message.sent_at));
      onSent(message);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.reply}>
      <TextField
        error={error}
        hint="Pracownik ROPS zobaczy ją w swoim dzienniku."
        label="Twoja wiadomość do ROPS"
        multiline
        onChangeText={(value) => {
          setBody(value);
          setSentAt(null);
        }}
        value={body}
      />
      <View style={styles.replyActions}>
        <Button
          busy={busy}
          icon={Send}
          label={busy ? "Wysyłam…" : "Wyślij wiadomość"}
          onPress={send}
          variant="primary"
        />
        {sentAt ? <Stamp at={sentAt} tone="ok" word="WYSŁANO" /> : null}
      </View>
    </View>
  );
}

export default function SubmissionScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const [load, setLoad] = useState<Load>({ kind: "loading" });

  const fetchThread = useCallback(
    async (quiet: boolean) => {
      if (!id) {
        return;
      }
      const token = await resolveToken(id);
      if (!token) {
        setLoad({ kind: "no-token" });
        return;
      }
      try {
        const thread = await api.thread(id, token);
        setLoad({ kind: "done", thread, token });
        await updateNeed(id, {
          number: thread.need.number,
          text: thread.need.text,
        });
      } catch (caught) {
        if (quiet) {
          return;
        }
        if (caught instanceof ApiError && caught.code === "not_found") {
          setLoad({ kind: "missing" });
          return;
        }
        setLoad({ kind: "error", message: errorMessage(caught) });
      }
    },
    [id]
  );

  useEffect(() => {
    fetchThread(false);
    const timer = setInterval(() => fetchThread(true), REFRESH_MS);
    return () => clearInterval(timer);
  }, [fetchThread]);

  const appendMessage = (message: ThreadMessage) =>
    setLoad((current) =>
      current.kind === "done"
        ? {
            ...current,
            thread: {
              ...current.thread,
              messages: [...current.thread.messages, message],
              need: { ...current.thread.need, status: "new" },
            },
          }
        : current
    );

  const back = (
    <View>
      <Button
        icon={ArrowLeft}
        label="Moje zgłoszenia"
        onPress={() => router.navigate("/zgloszenia")}
        variant="quiet"
      />
    </View>
  );

  if (load.kind !== "done") {
    return (
      <Screen>
        {back}
        {load.kind === "loading" ? (
          <Txt aria-live="polite" tone="soft">
            Wczytuję zgłoszenie…
          </Txt>
        ) : null}
        {load.kind === "no-token" || load.kind === "missing" ? (
          <Notice title="Nie możemy otworzyć tego zgłoszenia" tone="error">
            <Txt>
              Zgłoszenie otwiera się na urządzeniu, z którego je wysłano, albo z
              linku w e-mailu od ROPS. Sprawdź, czy link jest pełny.
            </Txt>
          </Notice>
        ) : null}
        {load.kind === "error" ? (
          <Notice tone="error">
            <View style={styles.reply}>
              <Txt>{load.message}</Txt>
              <Button
                label="Spróbuj ponownie"
                onPress={() => fetchThread(false)}
              />
            </View>
          </Notice>
        ) : null}
      </Screen>
    );
  }

  const { thread, token } = load;
  const code = numberCode(thread.need.number);
  const answered = thread.messages.some(
    (message) => message.direction === "to_author"
  );

  return (
    <Screen>
      <Head>
        <title>{`${code ? `Zgłoszenie ${code}` : "Zgłoszenie"} · ${APP_NAME}`}</title>
      </Head>
      {back}
      <Sheet raised>
        <View style={styles.header}>
          <Heading level={1}>
            {code ? `Zgłoszenie ${code}` : "Twoje zgłoszenie"}
          </Heading>
          <View style={styles.status}>
            <View
              style={[
                styles.dot,
                {
                  backgroundColor:
                    thread.need.status === "new"
                      ? colors.stamp
                      : colors.inkSoft,
                },
              ]}
            />
            <Txt tone="soft" variant="detail">
              {`${STATUS[thread.need.status]} · wysłane ${formatDate(thread.need.created_at)}`}
            </Txt>
          </View>
        </View>
        <View style={[styles.quote, { backgroundColor: colors.sunk }]}>
          <Txt>{thread.need.text}</Txt>
        </View>
      </Sheet>

      <Sheet>
        <Heading level={2}>Rozmowa z ROPS</Heading>
        {thread.messages.length > 0 ? (
          <View aria-live="polite" role="list" style={styles.messages}>
            {thread.messages.map((message) => (
              <Message key={message.id} message={message} />
            ))}
          </View>
        ) : (
          <Txt>
            ROPS jeszcze nie odpisał. Odpowiedź pojawi się tutaj
            {thread.can_email ? " i przyjdzie e-mailem." : "."}
          </Txt>
        )}
        {answered || thread.can_email ? null : (
          <View style={styles.reply}>
            <Heading level={3}>Chcesz dostać odpowiedź e-mailem?</Heading>
            <ContactForm
              needId={thread.need.id}
              nothingFits={false}
              onDone={() => fetchThread(true)}
              requireEmail
              submitLabel="Zapisz adres"
              token={token}
            />
          </View>
        )}
        {thread.need.status === "closed" ? (
          <Txt tone="soft">
            ROPS zamknął tę sprawę. Jeśli coś się zmieniło, napisz, a wróci do
            dziennika.
          </Txt>
        ) : null}
        <Reply id={thread.need.id} onSent={appendMessage} token={token} />
      </Sheet>
    </Screen>
  );
}

const styles = StyleSheet.create({
  dot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  header: {
    gap: space.md,
  },
  message: {
    borderRadius: radius.lg,
    gap: space.xs,
    padding: space.lg,
  },
  messages: {
    gap: space.md,
  },
  quote: {
    borderRadius: radius.lg,
    padding: space.lg,
  },
  reply: {
    gap: space.md,
  },
  replyActions: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.xl,
  },
  status: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
  },
});
