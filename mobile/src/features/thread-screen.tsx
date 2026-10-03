import Head from "expo-router/head";
import { Send } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { ThreadMessage } from "@/api/types";
import { APP_NAME } from "@/config";
import { ContactForm } from "@/features/contact-form";
import { Stamp } from "@/features/stamp";
import {
  messageTime,
  type ThreadKind,
  type ThreadView,
  useReply,
  useThread,
} from "@/hooks/use-thread";
import { formatDate } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const COPY = {
  idea: {
    back: "Zgłoś pomysł",
    backHref: "/pomysl" as const,
    title: "Pomysł",
    unnamed: "Twój pomysł",
  },
  need: {
    back: "Moje zgłoszenia",
    backHref: "/zgloszenia" as const,
    title: "Zgłoszenie",
    unnamed: "Twoje zgłoszenie",
  },
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
        {` · ${messageTime(message.sent_at)}`}
      </Txt>
      <Txt>{message.body}</Txt>
    </View>
  );
}

function Reply({
  kind,
  id,
  token,
  onSent,
}: {
  kind: ThreadKind;
  id: string;
  token: string;
  onSent: (message: ThreadMessage) => void;
}) {
  const { body, busy, error, send, sentAt, setBody } = useReply(
    kind,
    id,
    token,
    onSent
  );
  return (
    <View style={styles.group}>
      <TextField
        error={error}
        hint="Pracownik ROPS zobaczy ją w swoim dzienniku."
        label="Twoja wiadomość do ROPS"
        multiline
        onChangeText={setBody}
        value={body}
      />
      <View style={styles.replyActions}>
        <Button
          busy={busy}
          icon={Send}
          label={busy ? "Wysyłam" : "Wyślij wiadomość"}
          onPress={send}
          variant="primary"
        />
        {sentAt ? <Stamp at={sentAt} tone="ok" word="WYSŁANO" /> : null}
      </View>
    </View>
  );
}

function Conversation({
  kind,
  thread,
  token,
  onSent,
  onContact,
}: {
  kind: ThreadKind;
  thread: ThreadView;
  token: string;
  onSent: (message: ThreadMessage) => void;
  onContact: () => void;
}) {
  const { colors } = useTheme();
  const copy = COPY[kind];
  const answered = thread.messages.some(
    (message) => message.direction === "to_author"
  );
  return (
    <>
      <Head>
        <title>{`${thread.code ? `${copy.title} ${thread.code}` : copy.title} · ${APP_NAME}`}</title>
      </Head>
      <Sheet raised>
        <View style={styles.group}>
          <Heading level={1}>
            {thread.code ? `${copy.title} ${thread.code}` : copy.unnamed}
          </Heading>
          <View style={styles.status}>
            <View
              style={[
                styles.dot,
                {
                  backgroundColor: thread.waiting
                    ? colors.stamp
                    : colors.inkSoft,
                },
              ]}
            />
            <Txt tone="soft" variant="detail">
              {`${thread.statusLabel} · wysłane ${formatDate(thread.createdAt)}`}
            </Txt>
          </View>
        </View>
        {thread.text ? (
          <View style={[styles.quote, { backgroundColor: colors.sunk }]}>
            <Txt>{thread.text}</Txt>
          </View>
        ) : null}
      </Sheet>

      <Sheet>
        <Heading level={2}>Rozmowa z ROPS</Heading>
        {thread.messages.length > 0 ? (
          <View aria-live="polite" role="list" style={styles.group}>
            {thread.messages.map((message) => (
              <Message key={message.id} message={message} />
            ))}
          </View>
        ) : (
          <Txt>
            ROPS jeszcze nie odpisał. Odpowiedź pojawi się tutaj
            {thread.canEmail ? " i przyjdzie e-mailem." : "."}
          </Txt>
        )}
        {kind === "need" && !(answered || thread.canEmail) ? (
          <View style={styles.group}>
            <Heading level={3}>Chcesz dostać odpowiedź e-mailem?</Heading>
            <ContactForm
              needId={thread.id}
              nothingFits={false}
              onDone={onContact}
              requireEmail
              submitLabel="Zapisz adres"
              token={token}
            />
          </View>
        ) : null}
        {thread.closed ? (
          <Txt tone="soft">
            Ta sprawa jest zamknięta. Jeśli coś się zmieniło, napisz, a wróci do
            ROPS.
          </Txt>
        ) : null}
        <Reply id={thread.id} kind={kind} onSent={onSent} token={token} />
      </Sheet>
    </>
  );
}

export function ThreadScreen({
  kind,
  id,
}: {
  kind: ThreadKind;
  id: string | undefined;
}) {
  const { load, append, refresh } = useThread(kind, id);
  const copy = COPY[kind];
  return (
    <Screen back={copy.back} backFallback={copy.backHref}>
      {load.kind === "loading" ? (
        <Txt aria-live="polite" tone="soft">
          Wczytuję rozmowę.
        </Txt>
      ) : null}
      {load.kind === "no-token" ? (
        <Notice title="Nie możemy otworzyć tej rozmowy" tone="error">
          <Txt>
            Rozmowa otwiera się na urządzeniu, z którego ją zaczęto, albo z
            linku w e-mailu od ROPS. Sprawdź, czy link jest pełny.
          </Txt>
        </Notice>
      ) : null}
      {load.kind === "error" ? (
        <Notice tone="error">
          <View style={styles.group}>
            <Txt>{load.message}</Txt>
            <Button label="Spróbuj ponownie" onPress={() => refresh(false)} />
          </View>
        </Notice>
      ) : null}
      {load.kind === "done" ? (
        <Conversation
          kind={kind}
          onContact={() => refresh(true)}
          onSent={append}
          thread={load.thread}
          token={load.token}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  dot: {
    borderRadius: 4,
    height: 8,
    width: 8,
  },
  group: {
    gap: space.md,
  },
  message: {
    borderRadius: radius.lg,
    gap: space.xs,
    padding: space.lg,
  },
  quote: {
    borderRadius: radius.lg,
    padding: space.lg,
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
