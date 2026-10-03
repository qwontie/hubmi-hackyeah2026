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

type Tone = "default" | "soft" | "stamp" | "bad" | "ok" | "onStamp";

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
  style?: StyleProp<TextStyle>;
}

const headingRole = { 1: "h1", 2: "h2", 3: "h3" } as const;

export const Heading = function Heading({
  level,
  style,
  ref,
  children,
  ...rest
}: HeadingProps & { ref?: Ref<Text> }) {
  const { colors, type } = useTheme();
  const size = type[headingRole[level]];
  return (
    <Text
      aria-level={level}
      ref={ref}
      role="heading"
      style={[
        {
          color: colors.ink,
          fontFamily: level === 1 ? fonts["700"] : fonts["600"],
          fontSize: size,
          letterSpacing: size * (level === 1 ? -0.025 : -0.015),
          lineHeight: Math.round(size * (level === 1 ? 1.15 : 1.25)),
        },
        style,
      ]}
      {...rest}
    >
      {bindShortWords(children)}
    </Text>
  );
};
