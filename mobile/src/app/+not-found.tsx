import { router } from "expo-router";
import Head from "expo-router/head";
import { Search } from "lucide-react-native";
import { APP_NAME } from "@/config";
import { Button } from "@/ui/button";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function NotFoundScreen() {
  return (
    <Screen>
      <Head>
        <title>{`Nie ma takiej strony · ${APP_NAME}`}</title>
      </Head>
      <Sheet raised>
        <Heading level={1}>Nie ma takiej strony</Heading>
        <Txt>Adres może być niepełny albo strona została przeniesiona.</Txt>
        <Button
          icon={Search}
          label="Wróć do wyszukiwania"
          onPress={() => router.replace("/")}
          variant="primary"
        />
      </Sheet>
    </Screen>
  );
}
