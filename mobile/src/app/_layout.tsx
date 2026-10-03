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
import { StyleSheet, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { APP_NAME, ORGANIZATION_NAME } from "@/config";
import { SettingsProvider, useTheme } from "@/theme/settings";
import { radius } from "@/theme/tokens";
import { BottomBar, TopBar, useLastTabActive } from "@/ui/shell";
import { applyWebGlobals } from "@/ui/web-globals";

function Shell() {
  const { colors, reduceMotion, wide, highContrast } = useTheme();
  const lastTabActive = useLastTabActive();

  useEffect(() => {
    applyWebGlobals(colors, reduceMotion);
  }, [colors, reduceMotion]);

  return (
    <View style={[styles.root, { backgroundColor: colors.desk }]}>
      <Head>
        <title>{`${APP_NAME}: gotowe rozwiązania problemów społecznych`}</title>
        <meta
          content={`${ORGANIZATION_NAME}. Opisz problem zwykłymi słowami i znajdź sprawdzone innowacje społeczne z Małopolski.`}
          name="description"
        />
      </Head>
      <StatusBar style="dark" />
      <TopBar />
      <View
        style={[
          styles.stack,
          {
            backgroundColor: colors.board,
            borderColor: colors.ink,
            borderWidth: highContrast ? 2 : 0,
          },
          wide
            ? {
                borderRadius: radius.board,
                borderTopRightRadius: lastTabActive ? 0 : radius.board,
                marginBottom: 14,
                marginHorizontal: 14,
              }
            : {
                borderTopLeftRadius: radius.sheet,
                borderTopRightRadius: radius.sheet,
              },
        ]}
      >
        <Stack
          screenOptions={{
            animation: reduceMotion ? "none" : "default",
            contentStyle: { backgroundColor: colors.board },
            headerShown: false,
          }}
        />
      </View>
      <BottomBar />
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
        <Shell />
      </SettingsProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  stack: {
    flex: 1,
    overflow: "hidden",
  },
});
