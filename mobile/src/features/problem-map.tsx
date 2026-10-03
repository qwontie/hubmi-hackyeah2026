import { StyleSheet, View } from "react-native";
import Svg, { G, Path, Text as SvgText } from "react-native-svg";
import type { PowiatShape } from "@/lib/geo";
import { useTheme } from "@/theme/settings";
import { fonts } from "@/theme/tokens";

export interface MapCount {
  answered: number;
  open: number;
}

interface ProblemMapProps {
  counts: Record<string, MapCount>;
  height: number;
  onSelect: (slug: string) => void;
  selected: string | null;
  shade: (slug: string) => number | null;
  shapes: PowiatShape[];
  width: number;
}

const mix = (from: string, to: string, amount: number) => {
  const channel = (hex: string, index: number) =>
    Number.parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16);
  const parts = [0, 1, 2].map((index) =>
    Math.round(
      channel(from, index) +
        (channel(to, index) - channel(from, index)) * amount
    )
      .toString(16)
      .padStart(2, "0")
  );
  return `#${parts.join("")}`;
};

export function ProblemMap({
  counts,
  height,
  onSelect,
  selected,
  shade,
  shapes,
  width,
}: ProblemMapProps) {
  const { colors, highContrast } = useTheme();
  const most = Math.max(
    1,
    ...Object.values(counts).map((count) => count.open + count.answered)
  );
  const fillOf = (slug: string) => {
    if (slug === selected) {
      return colors.night;
    }
    if (highContrast) {
      return colors.paper;
    }
    const count = counts[slug];
    const total = count ? count.open + count.answered : 0;
    const level =
      total > 0 ? 0.25 + (0.75 * total) / most : (shade(slug) ?? 0) * 0.2;
    return mix(colors.paper, colors.sun, Math.min(1, level));
  };
  return (
    <View aria-hidden style={[styles.frame, { aspectRatio: width / height }]}>
      <Svg height="100%" viewBox={`0 0 ${width} ${height}`} width="100%">
        {shapes.map((shape) => (
          <Path
            d={shape.d}
            fill={fillOf(shape.slug)}
            key={shape.slug}
            onPress={() => onSelect(shape.slug)}
            stroke={highContrast ? colors.ink : colors.rule}
            strokeLinejoin="round"
            strokeWidth={3}
          />
        ))}
        {shapes.map((shape) => {
          const count = counts[shape.slug];
          const total = count ? count.open + count.answered : 0;
          if (total === 0) {
            return null;
          }
          const active = shape.slug === selected;
          return (
            <G key={shape.slug} pointerEvents="none">
              <SvgText
                fill={active ? colors.onNight : colors.ink}
                fontFamily={fonts.mono}
                fontSize={34}
                fontWeight="600"
                textAnchor="middle"
                x={shape.center.x}
                y={shape.center.y + 12}
              >
                {total}
              </SvgText>
            </G>
          );
        })}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    width: "100%",
  },
});
