import { router } from "expo-router";
import {
  ChevronRight,
  Lightbulb,
  type LucideIcon,
  MessageCircleHeart,
} from "lucide-react-native";
import { Pressable, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Glass } from "@/ui/glass";
import { Txt } from "@/ui/text";

const WASH = "rgba(252, 252, 255, 0.14)";

function ChoiceCard({
  icon: Icon,
  onPress,
  text,
  title,
}: {
  icon: LucideIcon;
  onPress: () => void;
  text: string;
  title: string;
}) {
  const { colors, reduceMotion, type, wide } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      role="button"
      style={({ pressed }) => [
        styles.press,
        wide && styles.pressWide,
        { transform: [{ scale: pressed && !reduceMotion ? 0.98 : 1 }] },
      ]}
    >
      <Glass interactive night style={[styles.card, wide && styles.cardWide]}>
        <View style={[styles.icon, { backgroundColor: WASH }]}>
          <Icon aria-hidden color={colors.onNight} size={28} strokeWidth={2} />
        </View>
        <View style={styles.body}>
          <Txt
            style={{
              fontSize: type.h3,
              letterSpacing: type.h3 * -0.02,
              lineHeight: Math.round(type.h3 * 1.2),
            }}
            tone="onNight"
            weight="600"
          >
            {title}
          </Txt>
          <Txt tone="onNightSoft" variant="label">
            {text}
          </Txt>
        </View>
        {wide ? null : (
          <ChevronRight aria-hidden color={colors.onNightSoft} size={26} />
        )}
      </Glass>
    </Pressable>
  );
}

export function EntryChoice({ onProblem }: { onProblem: () => void }) {
  const { wide } = useTheme();
  return (
    <View style={[styles.choices, wide && styles.choicesWide]}>
      <ChoiceCard
        icon={MessageCircleHeart}
        onPress={onProblem}
        text="Opisz go, a pokażemy sprawdzone rozwiązania."
        title="Mam problem"
      />
      <ChoiceCard
        icon={Lightbulb}
        onPress={() => router.navigate("/pomysl")}
        text="Zobacz, z czym mierzą się mieszkańcy, i zaproponuj rozwiązanie."
        title="Mam pomysł"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  body: {
    flex: 1,
    gap: space.xs + 2,
  },
  card: {
    alignItems: "center",
    borderRadius: radius.field,
    flexDirection: "row",
    gap: space.lg,
    minHeight: 124,
    paddingHorizontal: space.lg + 4,
    paddingVertical: space.lg + 2,
  },
  cardWide: {
    alignItems: "flex-start",
    flex: 1,
    flexDirection: "column",
    gap: space.xl,
    minHeight: 220,
    paddingHorizontal: space.xxl,
    paddingVertical: space.xxl,
  },
  choices: {
    gap: space.md + 2,
  },
  choicesWide: {
    alignItems: "stretch",
    flexDirection: "row",
    gap: space.lg + 4,
  },
  icon: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: 60,
    justifyContent: "center",
    width: 60,
  },
  press: {
    borderRadius: radius.field,
  },
  pressWide: {
    flex: 1,
  },
});
