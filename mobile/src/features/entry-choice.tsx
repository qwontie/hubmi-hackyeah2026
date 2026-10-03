import { router } from "expo-router";
import { ArrowRight } from "lucide-react-native";
import { type ReactNode, useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
  type ViewStyle,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { A11yControls } from "@/features/a11y-controls";
import { useTheme } from "@/theme/settings";
import { radius, space, tabBarSpace } from "@/theme/tokens";
import { nightAttr } from "@/ui/night";
import { WIDE_TOP } from "@/ui/screen";
import { Heading, Txt } from "@/ui/text";

const grow = (
  Platform.OS === "web"
    ? {
        transitionDuration: "420ms",
        transitionProperty: "flex-grow",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }
    : {}
) as ViewStyle;

const slide = (
  Platform.OS === "web"
    ? {
        transitionDuration: "320ms",
        transitionProperty: "transform",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }
    : {}
) as ViewStyle;

interface PanelProps {
  night: boolean;
  onPress: () => void;
  role: "button" | "link";
  text: string;
  title: string;
}

function Discs({ night, span }: { night: boolean; span: number }) {
  const { colors, wide } = useTheme();
  const outer = wide ? Math.min(span * 1.7, 1100) : span * 1.5;
  const inner = outer * 0.62;
  const tones = night
    ? [colors.nightRise, colors.dusk]
    : [colors.tone, colors.paper];
  return (
    <View aria-hidden pointerEvents="none" style={StyleSheet.absoluteFill}>
      <View
        style={{
          backgroundColor: tones[0],
          borderRadius: outer / 2,
          bottom: -outer * (wide ? 0.6 : 0.78),
          height: outer,
          left: (span - outer) / 2,
          position: "absolute",
          width: outer,
        }}
      />
      <View
        style={{
          backgroundColor: tones[1],
          borderRadius: inner / 2,
          bottom: -inner * (wide ? 0.66 : 0.86),
          height: inner,
          left: (span - inner) / 2,
          position: "absolute",
          width: inner,
        }}
      />
    </View>
  );
}

const usePanelPadding = (night: boolean): ViewStyle => {
  const { wide } = useTheme();
  const insets = useSafeAreaInsets();
  if (wide) {
    return { paddingBottom: 88, paddingHorizontal: 40, paddingTop: WIDE_TOP };
  }
  return {
    paddingBottom: night
      ? space.xl + radius.band
      : tabBarSpace + insets.bottom + space.sm,
    paddingHorizontal: space.xl - 2,
    paddingTop: night ? insets.top + 180 : space.xxl,
  };
};

function Panel({ night, onPress, role, text, title }: PanelProps) {
  const { colors, highContrast, reduceMotion, roomy, type, wide } = useTheme();
  const { width } = useWindowDimensions();
  const [hot, setHot] = useState(false);
  const span = wide ? width / 2 : width;
  const wideSize = roomy ? 96 : 72;
  const size = wide
    ? Math.round(wideSize * (type.body / 19))
    : Math.min(type.display, Math.floor((width - 44) / 6.2));
  const ink = night ? colors.onNight : colors.ink;
  const soft = night ? colors.onNightSoft : colors.inkSoft;
  const lively = hot && !reduceMotion;
  const lower = !(night || wide);
  return (
    <Pressable
      onBlur={() => setHot(false)}
      onFocus={() => setHot(true)}
      onHoverIn={() => setHot(true)}
      onHoverOut={() => setHot(false)}
      onPress={onPress}
      role={role}
      style={[
        styles.panel,
        grow,
        {
          backgroundColor: night ? colors.night : colors.ground,
          borderColor: colors.ink,
          borderTopWidth: highContrast && lower ? 2 : 0,
          flexGrow: lively && wide ? 1.22 : 1,
        },
        usePanelPadding(night),
        lower && styles.sheet,
      ]}
      {...nightAttr(night)}
    >
      <Discs night={night} span={span} />
      <View style={styles.body}>
        <Txt
          style={{
            color: ink,
            fontSize: size,
            letterSpacing: size * -0.04,
            lineHeight: Math.round(size * 1.02),
          }}
          weight="600"
        >
          {title}
        </Txt>
        <Txt
          style={[styles.text, { color: soft }]}
          variant={wide ? "h3" : "lead"}
        >
          {text}
        </Txt>
        <View
          style={[
            styles.arrow,
            slide,
            {
              backgroundColor: night ? colors.onNight : colors.stamp,
              transform: [{ translateX: lively ? 10 : 0 }],
            },
          ]}
        >
          <ArrowRight
            aria-hidden
            color={night ? colors.night : colors.onStamp}
            size={30}
            strokeWidth={2.2}
          />
        </View>
      </View>
    </Pressable>
  );
}

export function EntryChoice({
  onProblem,
  top,
}: {
  onProblem: () => void;
  top?: ReactNode;
}) {
  const { colors, wide } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View
      style={[
        styles.root,
        wide && styles.rootWide,
        { backgroundColor: colors.night },
      ]}
    >
      <Panel
        night
        onPress={onProblem}
        role="button"
        text="Opisz go swoimi słowami. Pokażemy rozwiązania, które już działają."
        title="Mam problem"
      />
      <Panel
        night={false}
        onPress={() => router.navigate("/pomysl")}
        role="link"
        text="Zobacz, z czym mierzą się mieszkańcy, i zaproponuj rozwiązanie."
        title="Mam pomysł"
      />
      <View
        pointerEvents="box-none"
        style={[
          styles.over,
          wide ? styles.overWide : { paddingTop: insets.top + space.sm },
        ]}
        {...nightAttr(true)}
      >
        {top}
        <View style={wide ? styles.controlsWide : undefined}>
          <A11yControls night />
        </View>
        <Heading level={1} night size="h3" style={styles.hidden}>
          Z czym przychodzisz?
        </Heading>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  arrow: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: 68,
    justifyContent: "center",
    marginTop: space.md,
    width: 68,
  },
  body: {
    gap: space.md,
    marginTop: "auto",
  },
  controlsWide: {
    maxWidth: 480,
  },
  hidden: {
    height: 1,
    overflow: "hidden",
    position: "absolute",
    width: 1,
  },
  over: {
    gap: space.lg,
    left: 0,
    paddingHorizontal: space.xl - 2,
    position: "absolute",
    right: 0,
    top: 0,
  },
  overWide: {
    paddingHorizontal: 40,
    right: "50%",
    top: WIDE_TOP + space.xl,
  },
  panel: {
    flexBasis: 0,
    flexGrow: 1,
    flexShrink: 1,
    overflow: "hidden",
  },
  root: {
    flex: 1,
  },
  rootWide: {
    flexDirection: "row",
  },
  sheet: {
    borderTopLeftRadius: radius.band,
    borderTopRightRadius: radius.band,
    marginTop: -radius.band,
  },
  text: {
    maxWidth: 520,
  },
});
