import {
  Geist_400Regular,
  Geist_500Medium,
  Geist_600SemiBold,
  Geist_700Bold,
  useFonts,
} from "@expo-google-fonts/geist";
import { GeistMono_600SemiBold } from "@expo-google-fonts/geist-mono";
import { Stack } from "expo-router";
import Head from "expo-router/head";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { Platform, StyleSheet, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { APP_NAME, ORGANIZATION_NAME } from "@/config";
import { ChromeProvider, useChromeTone } from "@/theme/chrome";
import { SettingsProvider, useTheme } from "@/theme/settings";
import { SkipLink, WideChrome } from "@/ui/shell";
import { applyWebGlobals } from "@/ui/web-globals";

function Shell() {
  const { colors, dark, reduceMotion } = useTheme();
  const night = useChromeTone() === "night";

  useEffect(() => {
    applyWebGlobals(colors, reduceMotion, night);
  }, [colors, reduceMotion, night]);

  return (
    <View style={[styles.root, { backgroundColor: colors.ground }]}>
      <Head>
        <title>{`${APP_NAME}: gotowe rozwiązania problemów społecznych`}</title>
        <meta
          content={`${ORGANIZATION_NAME}. Opisz problem zwykłymi słowami i znajdź sprawdzone innowacje społeczne z Małopolski.`}
          name="description"
        />
      </Head>
      <StatusBar style={night || dark ? "light" : "dark"} />
      <SkipLink />
      {Platform.OS === "web" ? <WideChrome /> : null}
      <Stack
        screenOptions={{
          animation: reduceMotion ? "none" : "default",
          contentStyle: { backgroundColor: colors.ground },
          headerShown: false,
        }}
      />
    </View>
  );
}

export default function RootLayout() {
  const [loaded, error] = useFonts({
    Geist_400Regular,
    Geist_500Medium,
    Geist_600SemiBold,
    Geist_700Bold,
    GeistMono_600SemiBold,
  });

  if (!(loaded || error)) {
    return null;
  }

  return (
    <SafeAreaProvider>
      <SettingsProvider>
        <ChromeProvider>
          <Shell />
        </ChromeProvider>
      </SettingsProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});
