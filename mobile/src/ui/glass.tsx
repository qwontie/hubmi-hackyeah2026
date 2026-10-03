import { GlassView, isLiquidGlassAvailable } from "expo-glass-effect";
import type { ReactNode, Ref } from "react";
import {
  Platform,
  type StyleProp,
  StyleSheet,
  View,
  type ViewProps,
  type ViewStyle,
} from "react-native";
import { useTheme } from "@/theme/settings";

const liquid = Platform.OS === "ios" && isLiquidGlassAvailable();

interface GlassProps extends ViewProps {
  children?: ReactNode;
  interactive?: boolean;
  night?: boolean;
  ref?: Ref<View>;
  style?: StyleProp<ViewStyle>;
}

export function Glass({
  children,
  interactive = false,
  night = false,
  style,
  ref,
  ...rest
}: GlassProps) {
  const { colors, dark, highContrast, reduceTransparency } = useTheme();

  if (liquid && !reduceTransparency) {
    return (
      <GlassView
        colorScheme={night || dark ? "dark" : "light"}
        glassEffectStyle="regular"
        isInteractive={interactive}
        ref={ref}
        style={style}
        {...rest}
      >
        {children}
      </GlassView>
    );
  }

  const solid = night ? colors.nightDeep : colors.paper;
  const translucent = night ? colors.glassNight : colors.glass;
  const edge = night ? colors.glassNightEdge : colors.glassEdge;
  const blur = Platform.OS === "web" && !reduceTransparency;

  return (
    <View
      ref={ref}
      style={[
        {
          backgroundColor: blur ? translucent : solid,
          borderColor: edge,
          borderWidth: highContrast ? 2 : 1,
        },
        blur && styles.blur,
        !highContrast && styles.lift,
        style,
      ]}
      {...rest}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  blur: Platform.select({
    default: {},
    web: { backdropFilter: "blur(26px) saturate(180%)" },
  }) as ViewStyle,
  lift: Platform.select({
    default: { elevation: 6 },
    ios: {
      shadowColor: "#2a2073",
      shadowOffset: { height: 10, width: 0 },
      shadowOpacity: 0.22,
      shadowRadius: 18,
    },
    web: {
      boxShadow:
        "0 12px 36px -14px rgba(42, 32, 115, 0.4), 0 1px 3px rgba(42, 32, 115, 0.08)",
    },
  }) as ViewStyle,
});
