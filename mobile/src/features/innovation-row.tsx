import { Link } from "expo-router";
import { ChevronRight } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import type { InnovationSummary } from "@/api/types";
import { CategoryIcon, CategoryTile } from "@/features/category-icon";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

interface InnovationRowProps {
  index?: number;
  innovation: InnovationSummary;
  last?: boolean;
  needId?: string;
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

export const innovationHref = (slug: string, needId?: string) =>
  ({
    params: needId ? { potrzeba: needId, slug } : { slug },
    pathname: "/innowacje/[slug]",
  }) as const;

export function InnovationRow({
  innovation,
  index,
  reason,
  last = false,
  needId,
}: InnovationRowProps) {
  const { colors, type, highContrast } = useTheme();
  const [hovered, setHovered] = useState(false);
  const meta = metaLine(innovation);
  return (
    <View
      role="listitem"
      style={
        last
          ? undefined
          : {
              borderBottomColor: highContrast ? colors.ink : colors.rule,
              borderBottomWidth: highContrast ? 2 : 1,
            }
      }
    >
      <Link asChild href={innovationHref(innovation.slug, needId)}>
        <Pressable
          onHoverIn={() => setHovered(true)}
          onHoverOut={() => setHovered(false)}
          role="link"
          style={styles.row}
        >
          {index === undefined ? (
            <CategoryTile size={48} slug={innovation.category.slug} />
          ) : (
            <Txt
              aria-hidden
              mono
              style={[styles.number, { fontSize: type.number }]}
              tone="stamp"
            >
              {index}
            </Txt>
          )}
          <View style={styles.body}>
            <Txt
              style={{
                color: hovered ? colors.stamp : colors.ink,
                fontSize: type.h3,
                letterSpacing: type.h3 * -0.02,
                lineHeight: Math.round(type.h3 * 1.2),
              }}
              weight="600"
            >
              {innovation.title}
            </Txt>
            <Txt tone="soft" variant="label">
              {reason ?? innovation.lead}
            </Txt>
            {meta ? (
              <View style={styles.meta}>
                {index === undefined ? null : (
                  <CategoryIcon
                    color={colors.inkSoft}
                    size={18}
                    slug={innovation.category.slug}
                  />
                )}
                <Txt style={styles.metaText} tone="soft" variant="small">
                  {meta}
                </Txt>
              </View>
            ) : null}
          </View>
          <ChevronRight
            aria-hidden
            color={colors.stamp}
            size={24}
            style={StyleSheet.flatten([
              styles.chevron,
              { transform: [{ translateX: hovered ? 4 : 0 }] },
            ])}
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
  meta: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
    marginTop: 2,
  },
  metaText: {
    flex: 1,
  },
  number: {
    minWidth: 26,
    paddingTop: 4,
  },
  row: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
    paddingVertical: space.lg + 4,
  },
});
