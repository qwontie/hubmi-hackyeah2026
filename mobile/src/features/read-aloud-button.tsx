import { Square, Volume2 } from "lucide-react-native";
import { Pressable, StyleSheet, useWindowDimensions } from "react-native";
import { useReadAloud } from "@/speech/read-aloud";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Glass } from "@/ui/glass";
import { Txt } from "@/ui/text";

export function ReadAloudButton({ text }: { text: string }) {
  const { supported, speaking, toggle } = useReadAloud();
  if (!supported) {
    return null;
  }
  return (
    <Button
      icon={speaking ? Square : Volume2}
      label={speaking ? "Zatrzymaj czytanie" : "Posłuchaj"}
      onPress={() => toggle(text)}
      pressed={speaking}
    />
  );
}

export function ReadAloudPill({
  text,
  night = false,
}: {
  night?: boolean;
  text: string;
}) {
  const { colors, reduceMotion } = useTheme();
  const { width } = useWindowDimensions();
  const { supported, speaking, toggle } = useReadAloud();
  if (!supported) {
    return null;
  }
  const Icon = speaking ? Square : Volume2;
  const ink = night ? colors.onNight : colors.stamp;
  const label = speaking ? "Zatrzymaj" : "Posłuchaj";
  const narrow = width < 380;
  return (
    <Pressable
      aria-label={speaking ? "Zatrzymaj czytanie" : "Posłuchaj strony"}
      aria-pressed={speaking}
      onPress={() => toggle(text)}
      role="button"
      style={({ pressed }) => [
        styles.press,
        { transform: [{ scale: pressed && !reduceMotion ? 0.96 : 1 }] },
      ]}
    >
      <Glass interactive night={night} style={styles.pill}>
        <Icon aria-hidden color={ink} size={22} strokeWidth={2.2} />
        {narrow ? null : (
          <Txt
            maxFontSizeMultiplier={1.3}
            style={{ color: ink }}
            variant="label"
            weight="600"
          >
            {label}
          </Txt>
        )}
      </Glass>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
    paddingHorizontal: space.lg + 2,
  },
  press: {
    borderRadius: radius.pill,
  },
});
