import { router } from "expo-router";
import Head from "expo-router/head";
import { ArrowRight, Bell } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { GrantCall } from "@/api/types";
import { APP_NAME } from "@/config";
import { useGrantCalls } from "@/hooks/use-grants";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

const date = (value: string) =>
  new Intl.DateTimeFormat("pl-PL", { dateStyle: "long" }).format(
    new Date(value)
  );

function CallCard({ call }: { call: GrantCall }) {
  const open = call.phase === "open";
  return (
    <Sheet raised={open}>
      <View style={styles.group}>
        <Txt tone={open ? "stamp" : "soft"} variant="detail" weight="600">
          {open ? "Nabór otwarty" : "Nabór zapowiedziany"}
          {call.demo ? " · Nabór pokazowy" : ""}
        </Txt>
        <Heading level={2}>{call.title}</Heading>
        <Txt tone="soft">
          {open
            ? `Wnioski do ${date(call.closes_at)}`
            : `Start ${date(call.opens_at)}`}
        </Txt>
      </View>
      <View style={styles.actions}>
        <Button
          icon={ArrowRight}
          label="Zobacz nabór"
          onPress={() =>
            router.push({
              params: { id: call.id },
              pathname: "/nabory/[id]",
            })
          }
          variant={open ? "primary" : "secondary"}
        />
      </View>
    </Sheet>
  );
}

export default function GrantCallsScreen() {
  const { calls, error, loading, retry } = useGrantCalls();
  return (
    <Screen back="Wróć" title="Nabory na innowacje" width={900}>
      <Head>
        <title>{`Nabory · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        <Txt tone="soft" variant="lead">
          Sprawdź otwarte i zapowiedziane nabory. Zapisany na tym urządzeniu
          pomysł możesz zamienić w roboczy wniosek.
        </Txt>
        <View style={styles.actions}>
          <Button
            icon={Bell}
            label="Powiadomienia o naborach"
            onPress={() => router.push("/nabory/powiadomienia")}
            variant="quiet"
          />
        </View>
      </View>
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
        <Notice title="Brak trwających naborów" tone="info">
          Nowe i zapowiedziane nabory pokażą się tutaj.
        </Notice>
      ) : null}
      <View role="list" style={styles.list}>
        {calls.map((call) => (
          <View key={call.id} role="listitem">
            <CallCard call={call} />
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { alignItems: "flex-start" },
  group: { gap: space.md },
  list: { gap: space.lg },
});
