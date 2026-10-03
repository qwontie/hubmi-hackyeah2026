import { Tabs } from "expo-router";
import { NativeTabs } from "expo-router/unstable-native-tabs";
import { Platform } from "react-native";
import type { SFSymbol } from "sf-symbols-typescript";
import { useTheme } from "@/theme/settings";
import { fonts } from "@/theme/tokens";
import { TABS, TabBar } from "@/ui/shell";

const renderTabBar = () => <TabBar />;

export default function TabsLayout() {
  const { colors } = useTheme();

  if (Platform.OS === "ios") {
    return (
      <NativeTabs
        labelStyle={{ fontFamily: fonts["600"] }}
        minimizeBehavior="onScrollDown"
        tintColor={colors.stamp}
      >
        {TABS.map((item) => (
          <NativeTabs.Trigger key={item.name} name={item.name}>
            <NativeTabs.Trigger.Icon
              sf={{
                default: item.sf.default as SFSymbol,
                selected: item.sf.selected as SFSymbol,
              }}
            />
            <NativeTabs.Trigger.Label>{item.label}</NativeTabs.Trigger.Label>
          </NativeTabs.Trigger>
        ))}
      </NativeTabs>
    );
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: colors.ground },
      }}
      tabBar={renderTabBar}
    >
      {TABS.map((item) => (
        <Tabs.Screen
          key={item.name}
          name={item.name}
          options={{ title: item.label }}
        />
      ))}
    </Tabs>
  );
}
