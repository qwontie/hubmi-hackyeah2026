import { CircleAlert, CircleCheck, Info } from "lucide-react-native";
import type { ReactNode } from "react";
import { StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Txt } from "./text";

interface NoticeProps {
  children?: ReactNode;
  live?: boolean;
  title?: string;
  tone: "error" | "success" | "info";
}

export function Notice({ tone, title, children, live = true }: NoticeProps) {
  const { colors, borderWidth } = useTheme();
  const scheme = {
    error: { color: colors.bad, icon: CircleAlert },
    info: { color: colors.stamp, icon: Info },
    success: { color: colors.ok, icon: CircleCheck },
  }[tone];
  const Icon = scheme.icon;
  const liveProps =
    live && tone === "error"
      ? { role: "alert" as const }
      : { "aria-live": live ? ("polite" as const) : undefined };
  return (
    <View
      {...liveProps}
      style={[
        styles.box,
        {
          backgroundColor: colors.paper,
          borderColor: scheme.color,
          borderWidth: Math.max(borderWidth, 1.5),
        },
      ]}
    >
      <Icon aria-hidden color={scheme.color} size={26} strokeWidth={2} />
      <View style={styles.body}>
        {title ? <Txt weight="600">{title}</Txt> : null}
        {typeof children === "string" ? (
          <Txt>{children}</Txt>
        ) : (
          (children ?? null)
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  body: {
    flex: 1,
    gap: space.sm,
  },
  box: {
    alignItems: "flex-start",
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.md,
    padding: space.lg + 2,
  },
});
