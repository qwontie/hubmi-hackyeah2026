import { StyleSheet, View } from "react-native";
import Svg, { Circle, G, Path, Text as SvgText } from "react-native-svg";
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

interface Badge {
  slug: string;
  total: number;
  x: number;
  y: number;
}

const separate = (a: Badge, b: Badge, gap: number) => {
  const distance = Math.hypot(b.x - a.x, b.y - a.y);
  if (distance >= gap) {
    return false;
  }
  const angle = distance > 0 ? Math.atan2(b.y - a.y, b.x - a.x) : 1;
  const push = (gap - distance) / 2 + 0.5;
  a.x -= Math.cos(angle) * push;
  a.y -= Math.sin(angle) * push;
  b.x += Math.cos(angle) * push;
  b.y += Math.sin(angle) * push;
  return true;
};

const placeBadges = (
  shapes: PowiatShape[],
  counts: Record<string, MapCount>,
  radius: number
) => {
  const wanted = shapes
    .map((shape) => {
      const count = counts[shape.slug];
      return {
        slug: shape.slug,
        total: count ? count.open + count.answered : 0,
        x: shape.center.x,
        y: shape.center.y,
      };
    })
    .filter((badge) => badge.total > 0)
    .sort((a, b) => b.total - a.total);
  const placed: Badge[] = wanted.map((badge) => ({ ...badge }));
  const gap = radius * 2 + 14;
  for (let pass = 0; pass < 80; pass += 1) {
    let moved = false;
    for (const [index, badge] of placed.entries()) {
      for (const other of placed.slice(index + 1)) {
        moved = separate(badge, other, gap) || moved;
      }
    }
    if (!moved) {
      break;
    }
  }
  return placed;
};

export function ProblemMap({
  counts,
  height,
  onSelect,
  selected,
  shapes,
  width,
}: ProblemMapProps) {
  const { colors, highContrast, type } = useTheme();
  const scale = Math.min(type.body / 19, 1.25);
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
    const level = total > 0 ? 0.25 + (0.75 * total) / most : 0;
    return mix(colors.paper, colors.sun, Math.min(1, level));
  };
  const radius = 36 * scale;
  const badges = placeBadges(shapes, counts, radius);
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
        {badges.map((badge) => (
          <G key={badge.slug} onPress={() => onSelect(badge.slug)}>
            <Circle
              cx={badge.x}
              cy={badge.y}
              fill={colors.paper}
              r={radius}
              stroke={
                badge.slug === selected || highContrast
                  ? colors.ink
                  : colors.stamp
              }
              strokeWidth={3}
            />
            <SvgText
              fill={colors.ink}
              fontFamily={fonts.mono}
              fontSize={42 * scale}
              fontWeight="600"
              textAnchor="middle"
              x={badge.x}
              y={badge.y + 15 * scale}
            >
              {badge.total}
            </SvgText>
          </G>
        ))}
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    width: "100%",
  },
});
