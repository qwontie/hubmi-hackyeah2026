import { Link } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import type { InnovationSummary } from "@/api/types";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

interface InnovationRowProps {
  index?: number;
  innovation: InnovationSummary;
  last?: boolean;
  reason?: string;
}

export const metaLine = (innovation: InnovationSummary) =>
  [
    innovation.category.name,
    innovation.has_video ? "film" : null,
    innovation.has_materials ? "materiały do pobrania" : null,
  ]
    .filter(Boolean)
    .join(" · ");

export function InnovationRow({
  innovation,
  index,
  reason,
  last = false,
}: InnovationRowProps) {
  const { colors, type, highContrast } = useTheme();
  const [hovered, setHovered] = useState(false);
  return (
    <View
      role="listitem"
      style={[
        styles.item,
        !last && {
          borderBottomColor: highContrast ? colors.ink : colors.rule,
          borderBottomWidth: highContrast ? 2 : 1,
          borderStyle: "dashed",
        },
      ]}
    >
      <Link
        asChild
        href={{
          params: { slug: innovation.slug },
          pathname: "/innowacje/[slug]",
        }}
      >
        <Pressable
          onHoverIn={() => setHovered(true)}
          onHoverOut={() => setHovered(false)}
          role="link"
          style={StyleSheet.flatten([
            styles.row,
            { backgroundColor: hovered ? colors.stampWash : "transparent" },
          ])}
        >
          {index === undefined ? null : (
            <Txt
              aria-hidden
              mono
              style={[styles.number, { fontSize: type.h3 }]}
              tone="stamp"
            >
              {index}
            </Txt>
          )}
          <View style={styles.body}>
            <Txt
              style={{
                fontSize: type.h3,
                lineHeight: Math.round(type.h3 * 1.3),
              }}
              weight="600"
            >
              {innovation.title}
            </Txt>
            {reason ? <Txt>{reason}</Txt> : null}
            <Txt tone="soft" variant="detail">
              {reason ? metaLine(innovation) : innovation.lead}
            </Txt>
            {reason ? null : (
              <Txt tone="soft" variant="detail">
                {metaLine(innovation)}
              </Txt>
            )}
          </View>
          <ChevronRight
            aria-hidden
            color={hovered ? colors.stamp : colors.inkSoft}
            size={24}
            style={styles.chevron}
          />
        </Pressable>
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  body: {
    flex: 1,
    gap: space.xs + 2,
  },
  chevron: {
    marginTop: 2,
  },
  item: {
    paddingVertical: space.xs,
  },
  number: {
    minWidth: 24,
  },
  row: {
    alignItems: "flex-start",
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: space.md,
    marginHorizontal: -space.sm,
    paddingHorizontal: space.sm,
    paddingVertical: space.md,
  },
});
