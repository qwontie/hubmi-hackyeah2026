import type { ReactNode } from "react";
import {
  Platform,
  type StyleProp,
  StyleSheet,
  View,
  type ViewProps,
  type ViewStyle,
} from "react-native";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";

interface SheetProps extends ViewProps {
  children: ReactNode;
  raised?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function Sheet({
  children,
  raised = false,
  style,
  ...rest
}: SheetProps) {
  const { colors, wide, highContrast } = useTheme();
  return (
    <View
      style={[
        styles.sheet,
        {
          backgroundColor: colors.paper,
          borderColor: highContrast ? colors.ink : colors.tone,
          borderWidth: highContrast ? 2 : 1,
          padding: wide ? space.xxl + 2 : space.xl - 2,
        },
        raised && !highContrast && styles.raised,
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  raised: Platform.select({
    default: { elevation: 4 },
    ios: {
      shadowColor: "#2a2073",
      shadowOffset: { height: 16, width: 0 },
      shadowOpacity: 0.14,
      shadowRadius: 24,
    },
    web: {
      boxShadow: "0 30px 50px -34px rgba(42, 32, 115, 0.5)",
    },
  }) as ViewStyle,
  sheet: {
    borderRadius: radius.sheet,
    gap: space.xl,
  },
});
