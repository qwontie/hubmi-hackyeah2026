import { useState } from "react";
import { Linking, Platform, Pressable, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

export interface RopsFactData {
  label: string;
  page: number | null;
  region_value: number | null;
  source_title: string;
  source_url: string;
  unit: string | null;
  value: number;
  year: number | null;
}

const amount = (value: number, unit: string | null) => {
  const number = value.toLocaleString("pl-PL");
  if (!unit) {
    return number;
  }
  return unit === "%" ? `${number}%` : `${number} ${unit}`;
};

const context = (fact: RopsFactData) =>
  [
    fact.year === null ? null : `${fact.year}`,
    fact.region_value === null
      ? null
      : `w całej Małopolsce ${amount(fact.region_value, fact.unit)}`,
  ]
    .filter(Boolean)
    .join(" · ");

function Source({ fact }: { fact: RopsFactData }) {
  const [hovered, setHovered] = useState(false);
  const href = fact.source_url;
  const page = fact.page ? `, s. ${fact.page}` : "";
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
      style={styles.source}
      {...webProps}
    >
      <Txt
        style={{ textDecorationLine: hovered ? "underline" : "none" }}
        tone="stamp"
        variant="detail"
        weight="500"
      >
        {`Źródło: ${fact.source_title}${page}`}
      </Txt>
    </Pressable>
  );
}

export function RopsFact({
  fact,
  first,
}: {
  fact: RopsFactData;
  first: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View
      role="listitem"
      style={[
        styles.fact,
        { borderTopColor: colors.rule },
        first && styles.first,
      ]}
    >
      <Txt>{fact.label}</Txt>
      <View style={styles.figure}>
        <Txt mono variant="h3" weight="600">
          {amount(fact.value, fact.unit)}
        </Txt>
        <Txt tone="soft" variant="detail">
          {context(fact)}
        </Txt>
      </View>
      <Source fact={fact} />
    </View>
  );
}

const styles = StyleSheet.create({
  fact: {
    borderTopWidth: 1,
    gap: space.xs,
    paddingBottom: space.sm,
    paddingTop: space.md,
  },
  figure: {
    alignItems: "baseline",
    columnGap: space.md,
    flexDirection: "row",
    flexWrap: "wrap",
  },
  first: {
    borderTopWidth: 0,
    paddingTop: 0,
  },
  source: {
    alignSelf: "flex-start",
    justifyContent: "center",
    minHeight: minTarget,
  },
});
