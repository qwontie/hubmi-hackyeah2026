import type { LucideIcon } from "lucide-react-native";
import { type Ref, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  type PressableProps,
  type StyleProp,
  StyleSheet,
  type View,
  type ViewStyle,
} from "react-native";
import { useTheme } from "@/theme/settings";
import { minTarget, type Palette, radius, space } from "@/theme/tokens";
import { Txt } from "./text";

type Variant = "primary" | "secondary" | "quiet";

const buttonPalette = ({
  colors,
  highContrast,
  hot,
  kind,
}: {
  colors: Palette;
  highContrast: boolean;
  hot: boolean;
  kind: Variant | "choice";
}) =>
  ({
    choice: {
      background: hot ? colors.tabHover : colors.tab,
      border: highContrast ? colors.ink : colors.tab,
      icon: colors.stamp,
      text: "default" as const,
    },
    primary: {
      background: hot ? colors.stampPress : colors.stamp,
      border: colors.stamp,
      icon: colors.onStamp,
      text: "onStamp" as const,
    },
    quiet: {
      background: hot ? colors.sunk : "transparent",
      border: "transparent",
      icon: colors.stamp,
      text: "stamp" as const,
    },
    secondary: {
      background: hot ? colors.sunk : colors.paper,
      border: colors.ruleStrong,
      icon: colors.stamp,
      text: "default" as const,
    },
  })[kind];

interface ButtonProps extends Omit<PressableProps, "style" | "children"> {
  busy?: boolean;
  fill?: boolean;
  icon?: LucideIcon;
  label: string;
  pressed?: boolean;
  size?: "regular" | "large";
  style?: StyleProp<ViewStyle>;
  variant?: Variant;
}

export const Button = function Button({
  label,
  icon: Icon,
  variant = "secondary",
  size = "regular",
  busy = false,
  pressed: toggled,
  fill = false,
  disabled,
  style,
  role = "button",
  ref,
  ...rest
}: ButtonProps & { ref?: Ref<View> }) {
  const { colors, borderWidth, reduceMotion, highContrast } = useTheme();
  const [hovered, setHovered] = useState(false);
  const inactive = disabled === true || busy;

  const palette = buttonPalette({
    colors,
    highContrast,
    hot: hovered && !inactive,
    kind: toggled === undefined ? variant : "choice",
  });

  const selected = toggled === true;

  return (
    <Pressable
      aria-busy={busy}
      aria-disabled={inactive}
      aria-pressed={role === "button" ? toggled : undefined}
      disabled={inactive}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      ref={ref}
      role={role}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: selected ? colors.stamp : palette.background,
          borderColor: selected ? colors.stamp : palette.border,
          borderWidth: variant === "quiet" ? 0 : borderWidth,
          minHeight: size === "large" ? 64 : minTarget,
          opacity: inactive && !busy ? 0.55 : 1,
          paddingHorizontal: size === "large" ? space.xl : space.lg,
          transform:
            pressed && !reduceMotion ? [{ scale: 0.98 }] : [{ scale: 1 }],
        },
        fill && styles.fill,
        style,
      ]}
      {...rest}
    >
      {busy ? (
        <ActivityIndicator
          color={variant === "primary" ? colors.onStamp : colors.stamp}
        />
      ) : null}
      {!busy && Icon ? (
        <Icon
          aria-hidden
          color={selected ? colors.onStamp : palette.icon}
          size={size === "large" ? 24 : 22}
          strokeWidth={2}
        />
      ) : null}
      <Txt
        style={styles.label}
        tone={selected ? "onStamp" : palette.text}
        variant={size === "large" ? "lead" : "label"}
        weight="600"
      >
        {label}
      </Txt>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    alignSelf: "flex-start",
    borderRadius: radius.md,
    flexDirection: "row",
    gap: space.sm,
    justifyContent: "center",
    maxWidth: "100%",
  },
  fill: {
    alignSelf: "stretch",
  },
  label: {
    flexShrink: 1,
    paddingVertical: space.xs,
  },
});
