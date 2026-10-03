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
          borderColor: colors.rule,
          borderWidth: highContrast ? 2 : StyleSheet.hairlineWidth,
          padding: wide ? space.xxl : space.lg + 2,
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
      shadowColor: "#2a2350",
      shadowOffset: { height: 12, width: 0 },
      shadowOpacity: 0.12,
      shadowRadius: 24,
    },
    web: {
      boxShadow: "0 0 0 1px #dddde3, 0 24px 48px -30px rgba(42, 35, 80, 0.35)",
    },
  }),
  sheet: {
    borderRadius: radius.sheet,
    gap: space.xl,
  },
});
