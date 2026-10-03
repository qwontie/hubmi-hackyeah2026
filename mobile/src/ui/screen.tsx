import { router } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import type { ReactNode, Ref } from "react";
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { A11yButton } from "@/features/a11y-controls";
import { RopsFooter } from "@/features/rops-footer";
import { useTheme } from "@/theme/settings";
import {
  contentWidth,
  minTarget,
  radius,
  space,
  tabBarSpace,
} from "@/theme/tokens";
import { Glass } from "./glass";
import { Txt } from "./text";

export const WIDE_TOP = 96;

const leave = (fallback: string) => {
  if (router.canGoBack()) {
    router.back();
  } else {
    router.replace(fallback as never);
  }
};

interface BackPillProps {
  fallback?: string;
  label: string;
  night?: boolean;
  onPress?: () => void;
}

export function BackPill({
  label,
  fallback = "/",
  night = false,
  onPress,
}: BackPillProps) {
  const { colors, reduceMotion } = useTheme();
  const ink = night ? colors.onNight : colors.ink;
  return (
    <Pressable
      accessibilityLabel={label}
      onPress={onPress ?? (() => leave(fallback))}
      role="button"
      style={({ pressed }) => [
        styles.pillPress,
        { transform: [{ scale: pressed && !reduceMotion ? 0.96 : 1 }] },
      ]}
    >
      <Glass interactive night={night} style={styles.pill}>
        <ChevronLeft aria-hidden color={ink} size={24} strokeWidth={2.2} />
        <Txt style={{ color: ink }} variant="label" weight="600">
          {label}
        </Txt>
      </Glass>
    </Pressable>
  );
}

export function PageHead({ children }: { children: ReactNode }) {
  return <View style={styles.head}>{children}</View>;
}

interface ScreenProps {
  back?: string;
  backFallback?: string;
  children: ReactNode;
  hero?: ReactNode;
  tabs?: boolean;
  trailing?: ReactNode;
  width?: number;
}

export const Screen = function Screen({
  back,
  backFallback,
  children,
  hero,
  tabs = false,
  trailing,
  width = contentWidth,
  ref,
}: ScreenProps & { ref?: Ref<ScrollView> }) {
  const { colors, wide } = useTheme();
  const insets = useSafeAreaInsets();
  const chromeTop = wide ? WIDE_TOP : insets.top + space.sm;
  const hasBar = Boolean(back || trailing) || !wide;
  const barSpace = hasBar ? minTarget + space.lg : 0;
  const bottomSpace =
    tabs && !wide ? tabBarSpace + insets.bottom : space.xxxl + insets.bottom;
  return (
    <View role="main" style={[styles.root, { backgroundColor: colors.ground }]}>
      <ScrollView
        contentContainerStyle={[styles.content, { paddingBottom: bottomSpace }]}
        keyboardShouldPersistTaps="handled"
        ref={ref}
        scrollIndicatorInsets={{ bottom: tabs ? tabBarSpace : 0 }}
      >
        {hero ? (
          <View
            style={[
              styles.hero,
              {
                backgroundColor: colors.tone,
                paddingHorizontal: wide ? space.xxl : space.xl - 2,
                paddingTop: chromeTop + barSpace + space.sm,
              },
            ]}
          >
            <View style={[styles.column, { maxWidth: width }]}>{hero}</View>
          </View>
        ) : null}
        <View
          style={[
            styles.pad,
            {
              paddingHorizontal: wide ? space.xxl : space.lg,
              paddingTop: hero ? space.xl : chromeTop + barSpace + space.sm,
            },
          ]}
        >
          <View style={[styles.column, { maxWidth: width }]}>
            {children}
            <RopsFooter />
          </View>
        </View>
      </ScrollView>
      {hasBar ? (
        <View
          pointerEvents="box-none"
          style={[
            styles.bar,
            {
              paddingHorizontal: wide ? space.xxl : space.lg,
              top: chromeTop,
            },
          ]}
        >
          <View
            pointerEvents="box-none"
            style={[styles.barRow, { maxWidth: width }]}
          >
            {back ? (
              <BackPill fallback={backFallback} label={back} />
            ) : (
              <View />
            )}
            <View style={styles.trail}>
              {trailing ?? null}
              <A11yButton />
            </View>
          </View>
        </View>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  bar: {
    alignItems: "center",
    left: 0,
    position: "absolute",
    right: 0,
  },
  barRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    width: "100%",
  },
  column: {
    alignSelf: "center",
    gap: space.lg,
    width: "100%",
  },
  content: {
    flexGrow: 1,
  },
  head: {
    gap: space.lg,
    paddingBottom: space.sm,
  },
  hero: {
    borderBottomLeftRadius: radius.band,
    borderBottomRightRadius: radius.band,
    paddingBottom: space.xxl - 2,
  },
  pad: {
    alignItems: "center",
  },
  pill: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.xs,
    minHeight: minTarget,
    paddingLeft: space.md,
    paddingRight: space.lg + 2,
    ...Platform.select({ default: {}, web: { cursor: "pointer" } }),
  },
  pillPress: {
    alignSelf: "flex-start",
    borderRadius: radius.pill,
  },
  root: {
    flex: 1,
  },
  trail: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
  },
});
