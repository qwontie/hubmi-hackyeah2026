import { Check } from "lucide-react-native";
import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, View } from "react-native";
import { categoryIcon } from "@/features/category-icon";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

interface FilterItem {
  count?: number;
  name: string;
  slug: string;
}

function Cell({
  active,
  item,
  onPress,
  wide,
}: {
  active: boolean;
  item: FilterItem;
  onPress: () => void;
  wide: boolean;
}) {
  const { colors, highContrast, type } = useTheme();
  const scaled = type.body > 19;
  const [hovered, setHovered] = useState(false);
  const Icon = active ? Check : categoryIcon(item.slug);
  const ink = active ? colors.onStamp : colors.ink;
  const rest = hovered ? colors.tone : colors.paper;
  return (
    <Pressable
      aria-pressed={active}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={onPress}
      role="button"
      style={[
        styles.cell,
        wide ? styles.cellWide : styles.cellNarrow,
        wide && scaled && styles.cellScaled,
        {
          backgroundColor: active ? colors.stamp : rest,
          borderColor: highContrast ? colors.ink : colors.tone,
          borderWidth: highContrast ? 2 : 1,
        },
      ]}
    >
      <View style={styles.icon}>
        <Icon
          aria-hidden
          color={active ? colors.onStamp : colors.stamp}
          size={24}
          strokeWidth={active ? 2.6 : 2}
        />
      </View>
      <Txt
        maxFontSizeMultiplier={1.3}
        style={[styles.name, { color: ink }]}
        variant="detail"
        weight={active ? "600" : "500"}
      >
        {item.name}
      </Txt>
      {item.count === undefined ? null : (
        <Txt
          maxFontSizeMultiplier={1.3}
          mono
          style={{ color: active ? colors.onStamp : colors.inkSoft }}
          variant="small"
        >
          {item.count}
        </Txt>
      )}
    </Pressable>
  );
}

export function CategoryFilter({
  items,
  label,
  onSelect,
  value,
}: {
  items: FilterItem[];
  label: string;
  onSelect: (slug: string) => void;
  value: string;
}) {
  const { wide } = useTheme();
  if (items.length === 0) {
    return null;
  }
  const cells = items.map((item) => (
    <Cell
      active={item.slug === value}
      item={item}
      key={item.slug}
      onPress={() => onSelect(item.slug)}
      wide={wide}
    />
  ));
  if (wide) {
    return (
      <View aria-label={label} role="group" style={styles.grid}>
        {cells}
      </View>
    );
  }
  return (
    <ScrollView
      aria-label={label}
      contentContainerStyle={styles.strip}
      horizontal
      role="group"
      showsHorizontalScrollIndicator={false}
      style={styles.bleed}
    >
      {cells}
    </ScrollView>
  );
}

const GUTTER = space.lg;

const styles = StyleSheet.create({
  bleed: {
    marginHorizontal: -GUTTER,
  },
  cell: {
    alignItems: "center",
    borderRadius: 18,
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget + 16,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
  cellNarrow: {
    maxWidth: 250,
  },
  cellScaled: {
    flexBasis: "48.5%",
  },
  cellWide: {
    flexBasis: "32.4%",
    minHeight: 92,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    rowGap: space.sm + 2,
  },
  icon: {
    flexShrink: 0,
    width: 24,
  },
  name: {
    flexGrow: 1,
    flexShrink: 1,
  },
  strip: {
    gap: space.sm,
    paddingHorizontal: GUTTER,
  },
});
