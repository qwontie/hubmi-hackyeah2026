import { Link } from "expo-router";
import { ArrowRight, Lightbulb } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import type { Problem } from "@/api/types";
import { CategoryIcon } from "@/features/category-icon";
import { problemStats } from "@/hooks/use-problems";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Sheet } from "@/ui/sheet";
import { Txt } from "@/ui/text";

export function ProblemCard({
  problem,
  onPropose,
}: {
  onPropose: () => void;
  problem: Problem;
}) {
  const { colors, type } = useTheme();
  const [hovered, setHovered] = useState(false);
  const href = {
    params: { id: problem.id },
    pathname: "/problemy/[id]",
  } as const;
  return (
    <Sheet style={styles.card}>
      <View style={[styles.tile, { backgroundColor: colors.tone }]}>
        <CategoryIcon size={26} slug={problem.category?.slug} />
      </View>
      <View style={styles.body}>
        <Link asChild href={href}>
          <Pressable
            onHoverIn={() => setHovered(true)}
            onHoverOut={() => setHovered(false)}
            role="link"
          >
            <Txt
              style={{
                color: hovered ? colors.stamp : colors.ink,
                fontSize: type.h3,
                letterSpacing: type.h3 * -0.025,
                lineHeight: Math.round(type.h3 * 1.15),
              }}
              weight="600"
            >
              {problem.title}
            </Txt>
          </Pressable>
        </Link>
        <Txt tone="soft" variant="label">
          {problem.summary}
        </Txt>
        <Txt tone="soft" variant="small" weight="500">
          {problemStats(problem).replaceAll(" · ", "\u00a0· ")}
        </Txt>
      </View>
      <View style={styles.foot}>
        <Button
          icon={Lightbulb}
          label="Zaproponuj rozwiązanie"
          onPress={onPropose}
          variant="primary"
        />
        <Link asChild href={href}>
          <Pressable
            aria-label={`Zobacz problem: ${problem.title}`}
            role="link"
            style={styles.open}
          >
            <Txt tone="stamp" variant="label" weight="600">
              Zobacz
            </Txt>
            <ArrowRight aria-hidden color={colors.stamp} size={22} />
          </Pressable>
        </Link>
      </View>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  body: {
    flexGrow: 1,
    gap: space.sm,
  },
  card: {
    flexGrow: 1,
    gap: space.md + 2,
  },
  foot: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
    justifyContent: "space-between",
  },
  open: {
    alignItems: "center",
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget + 4,
    paddingHorizontal: space.md,
  },
  tile: {
    alignItems: "center",
    borderRadius: 16,
    height: 52,
    justifyContent: "center",
    width: 52,
  },
});
