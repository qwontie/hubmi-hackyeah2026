import type { Ref } from "react";
import {
  type StyleProp,
  Text,
  type TextProps,
  type TextStyle,
} from "react-native";
import { bindShortWords } from "@/lib/typography";
import { useTheme } from "@/theme/settings";
import { fonts, type TypeRole, type Weight } from "@/theme/tokens";

export type Tone =
  | "default"
  | "soft"
  | "stamp"
  | "bad"
  | "ok"
  | "onStamp"
  | "onNight"
  | "onNightSoft";

interface TxtProps extends TextProps {
  mono?: boolean;
  style?: StyleProp<TextStyle>;
  tone?: Tone;
  variant?: TypeRole;
  weight?: Weight;
}

export const Txt = function Txt({
  variant = "body",
  tone = "default",
  weight = "400",
  mono = false,
  style,
  ref,
  children,
  ...rest
}: TxtProps & { ref?: Ref<Text> }) {
  const { colors, type, lineHeight } = useTheme();
  const size = type[variant];
  const color = {
    bad: colors.bad,
    default: colors.ink,
    ok: colors.ok,
    onNight: colors.onNight,
    onNightSoft: colors.onNightSoft,
    onStamp: colors.onStamp,
    soft: colors.inkSoft,
    stamp: colors.stamp,
  }[tone];
  return (
    <Text
      ref={ref}
      style={[
        {
          color,
          fontFamily: mono ? fonts.mono : fonts[weight],
          fontSize: size,
          fontVariant: mono ? ["tabular-nums"] : undefined,
          lineHeight: lineHeight(size),
        },
        style,
      ]}
      {...rest}
    >
      {bindShortWords(children)}
    </Text>
  );
};

interface HeadingProps extends TextProps {
  level: 1 | 2 | 3;
  night?: boolean;
  size?: TypeRole;
  style?: StyleProp<TextStyle>;
}

const headingRole = { 1: "h1", 2: "h2", 3: "h3" } as const;

export const Heading = function Heading({
  level,
  night = false,
  size: role,
  style,
  ref,
  children,
  ...rest
}: HeadingProps & { ref?: Ref<Text> }) {
  const { colors, type } = useTheme();
  const size = type[role ?? headingRole[level]];
  const tight = size >= 30;
  return (
    <Text
      aria-level={level}
      ref={ref}
      role="heading"
      style={[
        {
          color: night ? colors.onNight : colors.ink,
          fontFamily: fonts["600"],
          fontSize: size,
          letterSpacing: size * (tight ? -0.032 : -0.02),
          lineHeight: Math.round(size * (tight ? 1.08 : 1.22)),
        },
        style,
      ]}
      {...rest}
    >
      {bindShortWords(children)}
    </Text>
  );
};
