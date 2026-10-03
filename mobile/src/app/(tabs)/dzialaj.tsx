import Head from "expo-router/head";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { DoorRow, Doors, HUB_WIDTH, MyIdeas } from "@/features/contribute";
import { useStoredIdeas } from "@/storage/ideas";
import { space } from "@/theme/tokens";
import { PageHead, Screen } from "@/ui/screen";
import { Heading, Txt } from "@/ui/text";

export default function ContributeScreen() {
  const ideas = useStoredIdeas();
  return (
    <Screen tabs width={HUB_WIDTH}>
      <Head>
        <title>{`Działaj · ${APP_NAME}`}</title>
        <meta
          content="Zgłoś pomysł, złóż wniosek o grant albo zostań wolontariuszem ROPS w Krakowie."
          name="description"
        />
      </Head>
      <PageHead>
        <View style={styles.head}>
          <Heading level={1}>Jak chcesz działać?</Heading>
          <Txt tone="soft" variant="lead">
            Wybierz jedną z trzech dróg. Każde zgłoszenie czyta pracownik ROPS w
            Krakowie.
          </Txt>
        </View>
      </PageHead>
      <Doors
        doors={[
          {
            href: "/pomysl/nowy",
            text: "Opisz go w kilku zdaniach. Pracownik ROPS przeczyta i odpisze.",
            title: "Mam pomysł",
            tone: "night",
          },
          {
            href: "/nabory",
            text: "Zobacz, na co ROPS daje granty, i złóż wniosek.",
            title: "Nabory i wnioski",
            tone: "dusk",
          },
          {
            href: "/wolontariat",
            text: "Wypróbuj gotowe rozwiązanie u siebie i opisz, jak poszło.",
            title: "Wolontariat",
            tone: "day",
          },
        ]}
      />
      <DoorRow
        href="/pomysl/problemy"
        text="Zobacz problemy, które zgłosili mieszkańcy, i zaproponuj rozwiązanie."
        title="Nie masz jeszcze pomysłu?"
      />
      <MyIdeas ideas={ideas ?? []} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  head: {
    gap: space.md,
    maxWidth: 760,
  },
});
