import {
  ExternalLink as ExternalIcon,
  type LucideIcon,
} from "lucide-react-native";
import { useState } from "react";
import { Linking, Platform, Pressable, StyleSheet } from "react-native";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Txt } from "./text";

interface ExternalLinkProps {
  description?: string;
  href: string;
  icon?: LucideIcon;
  label: string;
}

export function ExternalLink({
  href,
  label,
  icon: Icon = ExternalIcon,
  description,
}: ExternalLinkProps) {
  const { colors, borderWidth } = useTheme();
  const [hovered, setHovered] = useState(false);
  const webProps =
    Platform.OS === "web"
      ? { href, hrefAttrs: { rel: "noopener noreferrer", target: "_blank" } }
      : {};
  return (
    <Pressable
      accessibilityHint="Otwiera się w nowym oknie"
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={
        Platform.OS === "web"
          ? undefined
          : () => {
              Linking.openURL(href).catch(() => undefined);
            }
      }
      role="link"
      style={[
        styles.link,
        {
          backgroundColor: hovered ? colors.sunk : colors.paper,
          borderColor: colors.ruleStrong,
          borderWidth,
        },
      ]}
      {...webProps}
    >
      <Icon aria-hidden color={colors.stamp} size={22} />
      <Txt style={styles.label} tone="stamp" weight="600">
        {label}
        {description ? (
          <Txt tone="soft" variant="detail">{` ${description}`}</Txt>
        ) : null}
      </Txt>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  label: {
    flexShrink: 1,
  },
  link: {
    alignItems: "center",
    alignSelf: "flex-start",
    borderRadius: radius.md,
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
});
