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
import { type Tone, Txt } from "./text";

type Variant = "primary" | "secondary" | "quiet" | "light";

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
      background: hot ? colors.toneHover : colors.tone,
      border: highContrast ? colors.ink : "transparent",
      icon: colors.stamp,
      text: "stamp" as const,
    },
    light: {
      background: hot ? colors.onNightSoft : colors.onNight,
      border: highContrast ? colors.onNight : "transparent",
      icon: colors.night,
      text: "night" as const,
    },
    primary: {
      background: hot ? colors.stampPress : colors.stamp,
      border: colors.stamp,
      icon: colors.onStamp,
      text: "onStamp" as const,
    },
    quiet: {
      background: hot ? colors.tone : "transparent",
      border: "transparent",
      icon: colors.stamp,
      text: "stamp" as const,
    },
    secondary: {
      background: hot ? colors.toneHover : colors.tone,
      border: highContrast ? colors.ink : "transparent",
      icon: colors.stamp,
      text: "stamp" as const,
    },
  })[kind];

const labelTone = (selected: boolean, text: Tone | "night"): Tone => {
  if (selected) {
    return "onStamp";
  }
  return text === "night" ? "default" : text;
};

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
          borderWidth: highContrast && variant !== "quiet" ? borderWidth : 0,
          minHeight: size === "large" ? 64 : minTarget + 8,
          opacity: inactive && !busy ? 0.55 : 1,
          paddingHorizontal: size === "large" ? space.xxl : space.xl,
          transform:
            pressed && !reduceMotion ? [{ scale: 0.97 }] : [{ scale: 1 }],
        },
        fill && styles.fill,
        style,
      ]}
      {...rest}
    >
      {busy ? (
        <ActivityIndicator
          color={variant === "primary" ? colors.onStamp : palette.icon}
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
        style={[
          styles.label,
          palette.text === "night" && !selected && { color: colors.night },
        ]}
        tone={labelTone(selected, palette.text)}
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
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.sm + 2,
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
