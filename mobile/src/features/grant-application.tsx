import { router } from "expo-router";
import {
  CircleCheck,
  FileText,
  type LucideIcon,
  PenLine,
  Send,
} from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { ApplicationStatus, GrantCall } from "@/api/types";
import { formatDate } from "@/lib/plural";
import type { StoredApplication } from "@/storage/applications";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const NBSP = " ";

export const longDate = (value: string) =>
  formatDate(value).replaceAll(" ", NBSP);

export const applicationState = (
  status: ApplicationStatus,
  submittedAt: string | null
) => {
  const sent = submittedAt ? `Wysłany ${longDate(submittedAt)}` : "Wysłany";
  return {
    accepted: `${sent} · przyjęty przez ROPS`,
    draft: "Wersja robocza, jeszcze niewysłana",
    in_review: `${sent} · w ocenie ROPS`,
    rejected: `${sent} · odrzucony przez ROPS`,
    submitted: sent,
  }[status];
};

export const openApplication = (id: string) =>
  router.push({ params: { id }, pathname: "/nabory/wniosek/[id]" });

export const startApplication = (callId: string, ideaId?: string) =>
  router.push({
    params: ideaId ? { nabor: callId, pomysl: ideaId } : { nabor: callId },
    pathname: "/nabory/wniosek/nowy",
  });

function StateLine({
  icon: Icon,
  text,
  tone,
}: {
  icon: LucideIcon;
  text: string;
  tone: "ok" | "stamp";
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.state}>
      <Icon
        aria-hidden
        color={tone === "ok" ? colors.ok : colors.stamp}
        size={22}
      />
      <Txt style={styles.grow} weight="500">
        {text}
      </Txt>
    </View>
  );
}

export function ApplicationRow({
  application,
  named = false,
}: {
  application: StoredApplication;
  named?: boolean;
}) {
  const { wide } = useTheme();
  const draft = application.status === "draft";
  return (
    <View style={[styles.row, wide && styles.rowWide]}>
      <View style={styles.rowText}>
        {named ? (
          <Txt variant="lead" weight="600">
            {application.callTitle}
          </Txt>
        ) : null}
        {application.ideaTitle ? (
          <Txt tone="soft" variant="detail">
            {`Pomysł: ${application.ideaTitle}`}
          </Txt>
        ) : null}
        <StateLine
          icon={draft ? PenLine : CircleCheck}
          text={applicationState(application.status, application.submittedAt)}
          tone={draft ? "stamp" : "ok"}
        />
      </View>
      <Button
        fill={!wide}
        icon={draft ? PenLine : FileText}
        label={draft ? "Dokończ wniosek" : "Zobacz wniosek"}
        onPress={() => openApplication(application.id)}
        variant={draft ? "primary" : "secondary"}
      />
    </View>
  );
}

export function MyApplications({
  applications,
}: {
  applications: StoredApplication[];
}) {
  const { colors } = useTheme();
  if (applications.length === 0) {
    return null;
  }
  return (
    <Sheet>
      <View style={styles.head}>
        <Heading level={2}>Moje wnioski</Heading>
        <Txt tone="soft">Zapisane na tym urządzeniu.</Txt>
      </View>
      <View role="list">
        {applications.map((application, index) => (
          <View
            key={application.id}
            role="listitem"
            style={[
              styles.item,
              { borderTopColor: colors.rule },
              index === 0 && styles.first,
            ]}
          >
            <ApplicationRow application={application} named />
          </View>
        ))}
      </View>
    </Sheet>
  );
}

export function CallAction({
  applications,
  call,
  ideaId,
}: {
  applications: StoredApplication[];
  call: GrantCall;
  ideaId?: string;
}) {
  const { wide } = useTheme();
  const mine = ideaId
    ? applications.filter((item) => item.ideaId === ideaId)
    : applications;
  if (mine.length > 0) {
    const sent = mine.filter((item) => item.status !== "draft");
    return (
      <View style={styles.group}>
        {sent.length > 0 ? (
          <Heading level={2} size="h3">
            {sent.length === mine.length
              ? "Twój wniosek jest wysłany"
              : "Twoje wnioski w tym naborze"}
          </Heading>
        ) : (
          <Heading level={2} size="h3">
            Masz niedokończony wniosek
          </Heading>
        )}
        {mine.map((application) => (
          <ApplicationRow application={application} key={application.id} />
        ))}
      </View>
    );
  }
  if (call.phase !== "open") {
    return (
      <Txt tone="soft">
        {call.phase === "upcoming"
          ? `Wnioski można składać od ${longDate(call.opens_at)}.`
          : "Nabór jest zakończony. Wniosków już nie przyjmujemy."}
      </Txt>
    );
  }
  return (
    <View style={styles.start}>
      <Button
        fill={!wide}
        icon={Send}
        label="Złóż wniosek"
        onPress={() => startApplication(call.id, ideaId)}
        size="large"
        variant="primary"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  first: { borderTopWidth: 0 },
  group: { gap: space.md },
  grow: { flex: 1 },
  head: { gap: space.xs },
  item: { borderTopWidth: 1, paddingVertical: space.lg },
  row: { gap: space.md },
  rowText: { flex: 1, gap: space.xs },
  rowWide: { alignItems: "center", flexDirection: "row", gap: space.xl },
  start: { alignItems: "flex-start" },
  state: { alignItems: "flex-start", flexDirection: "row", gap: space.sm },
});
