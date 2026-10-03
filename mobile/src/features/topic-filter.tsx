import { Check, ChevronDown, ChevronUp, Tag, X } from "lucide-react-native";
import { useRef, useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

interface TopicItem {
  count: number;
  name: string;
  slug: string;
}

interface TopicFilterProps {
  emptyLabel: string;
  items: TopicItem[];
  label: string;
  onSelect: (slug: string) => void;
  value: string;
}

const columnWidth = (wide: boolean, scaled: boolean) => {
  if (!wide) {
    return "100%";
  }
  return scaled ? "50%" : "33.33%";
};

function Topic({
  active,
  item,
  onPress,
  width,
}: {
  active: boolean;
  item: TopicItem;
  onPress: () => void;
  width: "100%" | "50%" | "33.33%";
}) {
  const { colors } = useTheme();
  const [hovered, setHovered] = useState(false);
  const strong = active || hovered;
  return (
    <Pressable
      aria-label={`${item.name}, ${item.count}`}
      aria-pressed={active}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={onPress}
      role="button"
      style={[styles.topic, { width }]}
    >
      <View style={styles.mark}>
        {active ? (
          <Check aria-hidden color={colors.stamp} size={20} strokeWidth={2.6} />
        ) : null}
      </View>
      <Txt
        style={[styles.grow, { color: strong ? colors.stamp : colors.ink }]}
        variant="detail"
        weight={active ? "600" : "400"}
      >
        {item.name}
      </Txt>
      <Txt mono tone="soft" variant="small">
        {item.count}
      </Txt>
    </Pressable>
  );
}

export function TopicFilter({
  emptyLabel,
  items,
  label,
  onSelect,
  value,
}: TopicFilterProps) {
  const { colors, highContrast, type, wide } = useTheme();
  const [open, setOpen] = useState(false);
  const trigger = useRef<View>(null);
  if (items.length === 0) {
    return null;
  }
  const chosen = items.find((item) => item.slug === value);
  const Chevron = open ? ChevronUp : ChevronDown;
  const width = columnWidth(wide, type.body > 19);
  const pick = (slug: string) => {
    onSelect(slug);
    setOpen(false);
    trigger.current?.focus();
  };
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.paper,
          borderColor: highContrast ? colors.ink : colors.tone,
          borderWidth: highContrast ? 2 : 1,
        },
      ]}
    >
      <View style={styles.bar}>
        <Pressable
          aria-expanded={open}
          aria-label={`${label}: ${chosen?.name ?? emptyLabel}. ${open ? "Zwiń listę" : "Wybierz z listy"}`}
          onPress={() => setOpen((current) => !current)}
          ref={trigger}
          role="button"
          style={styles.trigger}
        >
          <Tag aria-hidden color={colors.stamp} size={24} strokeWidth={2} />
          <Txt
            style={styles.grow}
            variant="detail"
            weight={chosen ? "600" : "500"}
          >
            {chosen?.name ?? emptyLabel}
          </Txt>
          <Chevron aria-hidden color={colors.inkSoft} size={22} />
        </Pressable>
        {chosen ? (
          <Pressable
            aria-label="Usuń wybór tematu"
            onPress={() => onSelect(chosen.slug)}
            role="button"
            style={styles.clear}
          >
            <X aria-hidden color={colors.inkSoft} size={22} />
          </Pressable>
        ) : null}
      </View>
      {open ? (
        <View
          aria-label={label}
          role="group"
          style={[styles.list, { borderTopColor: colors.tone }]}
        >
          {items.map((item) => (
            <Topic
              active={item.slug === value}
              item={item}
              key={item.slug}
              onPress={() => pick(item.slug)}
              width={width}
            />
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    alignItems: "center",
    flexDirection: "row",
    paddingRight: space.xs,
  },
  card: {
    borderRadius: 18,
    overflow: "hidden",
  },
  clear: {
    alignItems: "center",
    height: minTarget,
    justifyContent: "center",
    width: minTarget,
  },
  grow: {
    flexGrow: 1,
    flexShrink: 1,
  },
  list: {
    borderTopWidth: 1,
    flexDirection: "row",
    flexWrap: "wrap",
    paddingHorizontal: space.sm,
    paddingVertical: space.sm,
  },
  mark: {
    width: 20,
  },
  topic: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
    paddingHorizontal: space.sm,
    paddingVertical: space.xs,
  },
  trigger: {
    alignItems: "center",
    flexDirection: "row",
    flexGrow: 1,
    flexShrink: 1,
    gap: space.md,
    minHeight: minTarget + 16,
    paddingHorizontal: space.lg,
  },
});
