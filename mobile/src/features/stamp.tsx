import { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { fonts, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

interface StampProps {
  at: Date;
  number?: number | null;
  word: string;
}

const dayFormat = (date: Date) =>
  date.toLocaleDateString("pl-PL", { day: "numeric", month: "long" });

const timeFormat = (date: Date) =>
  date.toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" });

export function Stamp({ word, at, number }: StampProps) {
  const { colors, reduceMotion } = useTheme();
  const progress = useRef(new Animated.Value(reduceMotion ? 1 : 0)).current;

  useEffect(() => {
    if (reduceMotion) {
      progress.setValue(1);
      return;
    }
    progress.setValue(0);
    Animated.timing(progress, {
      duration: 420,
      easing: Easing.bezier(0.2, 0.9, 0.3, 1.2),
      toValue: 1,
      useNativeDriver: false,
    }).start();
  }, [progress, reduceMotion]);

  const day = dayFormat(at);
  const time = timeFormat(at);
  const code = number ? `HUB/${String(number).padStart(4, "0")}` : null;
  const label = [
    `${word.charAt(0)}${word.slice(1).toLowerCase()}`,
    day,
    `o godzinie ${time}`,
    code ? `numer ${code}` : null,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <Animated.View
      accessibilityLabel={label}
      accessible
      role="img"
      style={{
        opacity: progress,
        transform: [
          {
            scale: progress.interpolate({
              inputRange: [0, 1],
              outputRange: [1.35, 1],
            }),
          },
          {
            rotate: progress.interpolate({
              inputRange: [0, 1],
              outputRange: ["-8deg", "-3deg"],
            }),
          },
        ],
      }}
    >
      <View style={[styles.outer, { borderColor: colors.stamp }]}>
        <View style={[styles.inner, { borderColor: colors.stamp }]}>
          <Txt
            style={{
              fontFamily: fonts["700"],
              fontSize: 15,
              letterSpacing: 2,
              lineHeight: 18,
            }}
            tone="stamp"
          >
            {word}
          </Txt>
          <Txt
            style={{ fontSize: 14, lineHeight: 18 }}
            tone="stamp"
            weight="500"
          >
            {day}
          </Txt>
          <Txt mono style={{ fontSize: 13, lineHeight: 17 }} tone="stamp">
            {code ? `godz. ${time} · ${code}` : `godz. ${time}`}
          </Txt>
        </View>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  inner: {
    alignItems: "center",
    borderRadius: 5,
    borderWidth: 1,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
  },
  outer: {
    alignSelf: "flex-start",
    borderRadius: 8,
    borderWidth: 2,
    padding: 2,
  },
});
