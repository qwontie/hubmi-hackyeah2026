import { router } from "expo-router";
import Head from "expo-router/head";
import { StyleSheet, View } from "react-native";
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

export default function GrantCallsScreen() {
  const { calls, error, loading, retry } = useGrantCalls();
  return (
    <Screen back="Wróć" width={900}>
      <Head>
        <title>{`Nabory · ${APP_NAME}`}</title>
      </Head>
      <View style={styles.group}>
        <Heading level={1}>Nabory na innowacje</Heading>
        <Txt tone="soft" variant="lead">
          Sprawdź otwarte i zapowiedziane nabory. Zapisany na tym urządzeniu
          pomysł możesz zamienić w roboczy wniosek.
        </Txt>
        <Button
          label="Powiadomienia o naborach"
          onPress={() => router.push("/nabory/powiadomienia")}
          variant="secondary"
        />
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
            <Sheet>
              <View style={styles.group}>
                <Txt
                  tone={call.phase === "open" ? "stamp" : "soft"}
                  weight="600"
                >
                  {call.phase === "open"
                    ? "Nabór otwarty"
                    : "Nabór zapowiedziany"}
                  {call.demo ? " · Nabór pokazowy" : ""}
                </Txt>
                <Heading level={2}>{call.title}</Heading>
                <Txt>
                  {call.phase === "open" ? "Do" : "Od"}{" "}
                  {date(call.phase === "open" ? call.closes_at : call.opens_at)}
                </Txt>
                <Button
                  label="Zobacz nabór"
                  onPress={() =>
                    router.push({
                      params: { id: call.id },
                      pathname: "/nabory/[id]",
                    })
                  }
                />
              </View>
            </Sheet>
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  group: { gap: space.md },
  list: { gap: space.lg },
});
