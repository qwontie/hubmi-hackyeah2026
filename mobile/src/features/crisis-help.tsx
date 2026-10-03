import { Phone } from "lucide-react-native";
import { Linking, Platform, Pressable, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Heading, Txt } from "@/ui/text";

const LINES = [
  {
    about: "telefon zaufania dla dorosłych w kryzysie emocjonalnym",
    dial: "116123",
    number: "116 123",
  },
  {
    about:
      "Centrum Wsparcia dla osób w kryzysie psychicznym, bezpłatnie, całą dobę",
    dial: "800702222",
    number: "800 70 2222",
  },
  {
    about: "numer alarmowy, gdy zagrożone jest życie lub zdrowie",
    dial: "112",
    number: "112",
  },
];

function Line({ line }: { line: (typeof LINES)[number] }) {
  const { colors } = useTheme();
  const href = `tel:${line.dial}`;
  return (
    <Pressable
      aria-label={`Zadzwoń ${line.number}: ${line.about}`}
      onPress={
        Platform.OS === "web"
          ? undefined
          : () => {
              Linking.openURL(href).catch(() => undefined);
            }
      }
      role="link"
      style={[styles.line, { backgroundColor: colors.tone }]}
      {...(Platform.OS === "web" ? { href } : {})}
    >
      <Phone aria-hidden color={colors.stamp} size={24} strokeWidth={2.2} />
      <View style={styles.words}>
        <Txt mono tone="stamp" variant="h3" weight="600">
          {line.number}
        </Txt>
        <Txt variant="label">{line.about}</Txt>
      </View>
    </Pressable>
  );
}

export function CrisisHelp() {
  const { colors, highContrast } = useTheme();
  return (
    <View
      aria-label="Pomoc w kryzysie"
      role="group"
      style={[
        styles.block,
        {
          backgroundColor: colors.paper,
          borderColor: highContrast ? colors.ink : colors.stamp,
        },
      ]}
    >
      <View style={styles.head}>
        <Heading level={2} size="h3">
          Potrzebujesz pomocy teraz?
        </Heading>
        <Txt tone="soft">
          Jeśli jest Ci bardzo trudno albo ktoś jest w niebezpieczeństwie, nie
          czekaj. Zadzwoń:
        </Txt>
      </View>
      <View style={styles.lines}>
        {LINES.map((line) => (
          <Line key={line.dial} line={line} />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    borderRadius: radius.sheet,
    borderWidth: 2,
    gap: space.md,
    padding: space.lg + 2,
  },
  head: {
    gap: space.xs,
  },
  line: {
    alignItems: "center",
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget + 16,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
  lines: {
    gap: space.sm,
  },
  words: {
    flex: 1,
  },
});
