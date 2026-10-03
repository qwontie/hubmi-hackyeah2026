import { router } from "expo-router";
import Head from "expo-router/head";
import { ArrowRight, Bell } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { GrantCall } from "@/api/types";
import { APP_NAME } from "@/config";
import {
  CallAction,
  longDate,
  MyApplications,
} from "@/features/grant-application";
import {
  applicationsOfCall,
  useGrantCalls,
  useMyApplications,
} from "@/hooks/use-grants";
import type { StoredApplication } from "@/storage/applications";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

function CallCard({
  applications,
  call,
}: {
  applications: StoredApplication[];
  call: GrantCall;
}) {
  const open = call.phase === "open";
  return (
    <Sheet raised={open}>
      <View style={styles.group}>
        <Txt tone={open ? "stamp" : "soft"} variant="detail" weight="600">
          {open ? "Nabór otwarty" : "Nabór zapowiedziany"}
          {call.demo ? " · Nabór pokazowy" : ""}
        </Txt>
        <Heading level={2}>{call.title}</Heading>
        <Txt tone="soft">
          {open
            ? `Wnioski do ${longDate(call.closes_at)}`
            : `Start ${longDate(call.opens_at)}`}
        </Txt>
      </View>
      <CallAction applications={applications} call={call} />
      <View style={styles.inset}>
        <Button
          icon={ArrowRight}
          label="O naborze i pytania z wniosku"
          onPress={() =>
            router.push({
              params: { id: call.id },
              pathname: "/nabory/[id]",
            })
          }
          variant="quiet"
        />
      </View>
    </Sheet>
  );
}

export default function GrantCallsScreen() {
  const { calls, error, loading, retry } = useGrantCalls();
  const applications = useMyApplications();
  const elsewhere = (applications ?? []).filter(
    (item) => !calls.some((call) => call.id === item.callId)
  );
  return (
    <Screen
      back="Działaj"
      backFallback="/dzialaj"
      title="Nabory i wnioski"
      width={900}
    >
      <Head>
        <title>{`Nabory i wnioski · ${APP_NAME}`}</title>
      </Head>
      <Txt variant="lead">
        Nabór to konkurs, w którym ROPS daje granty na pomysły mieszkańców i
        organizacji. Wniosek to Twoje odpowiedzi na pytania naboru.
      </Txt>
      {loading ? <Txt aria-live="polite">Wczytuję nabory.</Txt> : null}
      {error ? (
        <Notice title="Nie udało się wczytać naborów" tone="error">
          <View style={styles.group}>
            <Txt>{error}</Txt>
            <Button label="Spróbuj ponownie" onPress={retry} />
          </View>
        </Notice>
      ) : null}
      {!(loading || error) && calls.length === 0 ? (
        <Notice title="Teraz nie ma naboru" tone="info">
          Nowe i zapowiedziane nabory pokażą się tutaj. Możesz zapisać się na
          powiadomienie e-mailem.
        </Notice>
      ) : null}
      <View role="list" style={styles.list}>
        {calls.map((call) => (
          <View key={call.id} role="listitem">
            <CallCard
              applications={applicationsOfCall(applications, call.id)}
              call={call}
            />
          </View>
        ))}
      </View>
      {loading ? null : <MyApplications applications={elsewhere} />}
      <View style={styles.actions}>
        <Button
          icon={Bell}
          label="Powiadom mnie e-mailem o nowych naborach"
          onPress={() => router.push("/nabory/powiadomienia")}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: "flex-start" },
  group: { gap: space.md },
  inset: { alignItems: "flex-start", marginLeft: -space.xl },
  list: { gap: space.lg },
});
