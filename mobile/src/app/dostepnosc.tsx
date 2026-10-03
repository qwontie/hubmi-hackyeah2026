import Head from "expo-router/head";
import { StyleSheet, View } from "react-native";
import { APP_NAME } from "@/config";
import { useSettings } from "@/theme/settings";
import { space, textScales } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Checkbox } from "@/ui/field";
import { Screen } from "@/ui/screen";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export default function AccessibilityScreen() {
  const { settings, update, theme } = useSettings();
  const { wide } = theme;
  return (
    <Screen back="Wróć">
      <Head>
        <title>{`Dostępność · ${APP_NAME}`}</title>
      </Head>
      <Sheet raised>
        <View style={styles.group}>
          <Heading level={1}>Dostępność</Heading>
          <Txt tone="soft">
            Ustawienia zapisują się na tym urządzeniu i działają od razu.
          </Txt>
        </View>
      </Sheet>
      <Sheet>
        <View style={styles.group}>
          <Heading level={2} nativeID="text-size">
            Wielkość tekstu
          </Heading>
          <View
            aria-labelledby="text-size"
            role="radiogroup"
            style={wide ? styles.options : styles.group}
          >
            {textScales.map((scale) => (
              <Button
                aria-checked={settings.textScale === scale.key}
                fill={!wide}
                key={scale.key}
                label={scale.label}
                onPress={() => update({ textScale: scale.key })}
                pressed={settings.textScale === scale.key}
                role="radio"
              />
            ))}
          </View>
        </View>
        <View style={styles.group}>
          <Heading level={2}>Wygląd i ruch</Heading>
          <Checkbox
            checked={settings.highContrast}
            label="Wysoki kontrast: czarny tekst na białym tle i grubsze ramki"
            onChange={(value) => update({ highContrast: value })}
          />
          <Checkbox
            checked={settings.reduceMotion}
            label="Ogranicz animacje"
            onChange={(value) => update({ reduceMotion: value })}
          />
        </View>
        <View style={styles.group}>
          <Heading level={2}>Głos</Heading>
          <Txt>
            Przy wynikach i opisach rozwiązań jest przycisk „Przeczytaj na
            głos”. Opis problemu możesz też podyktować przyciskiem „Powiedz
            zamiast pisać”, jeśli przeglądarka na to pozwala.
          </Txt>
        </View>
      </Sheet>
    </Screen>
  );
}

const styles = StyleSheet.create({
  group: {
    gap: space.md,
  },
  options: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
});
