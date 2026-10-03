import { MessageCircleQuestion, Sparkles } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { Canvas, IdeaDraft, IdeaOptions } from "@/api/types";
import { InnovationRow } from "@/features/innovation-row";
import { useIdeaAssistant } from "@/hooks/use-idea";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { TextField } from "@/ui/field";
import { Notice } from "@/ui/notice";
import { Heading, Txt } from "@/ui/text";

interface IdeaAssistantProps {
  canvas: Partial<Canvas>;
  draft: IdeaDraft;
  onCanvas: (canvas: Partial<Canvas>) => void;
  options: IdeaOptions;
}

function CanvasView({
  canvas,
  options,
}: {
  canvas: Partial<Canvas>;
  options: IdeaOptions;
}) {
  const { colors } = useTheme();
  const filled = options.canvas_fields.filter((item) => canvas[item.field]);
  if (filled.length === 0) {
    return null;
  }
  return (
    <View role="list" style={styles.list}>
      {filled.map((item) => (
        <View
          key={item.field}
          role="listitem"
          style={[styles.canvasRow, { backgroundColor: colors.sunk }]}
        >
          <Txt tone="soft" variant="detail" weight="600">
            {item.name}
          </Txt>
          <Txt>{canvas[item.field]}</Txt>
        </View>
      ))}
    </View>
  );
}

export function IdeaAssistant({
  draft,
  options,
  canvas,
  onCanvas,
}: IdeaAssistantProps) {
  const { answer, busy, drafts, error, result, run } = useIdeaAssistant(
    draft,
    canvas,
    onCanvas
  );

  const total = options.canvas_fields.length;
  const done = result ? total - result.missing.length : 0;

  return (
    <View style={styles.block}>
      <Heading level={2}>Asystent pomysłu</Heading>
      <Txt>
        Asystent to sztuczna inteligencja. Zada kilka pytań, które pomogą
        rozwinąć pomysł, i podpowie, co już działa w Małopolsce. Nic nie wymyśla
        za Ciebie.
      </Txt>
      {result ? (
        <View aria-live="polite" style={styles.block}>
          <Txt weight="600">{`Uzupełniono ${done} z ${total} pól kanwy`}</Txt>
          <CanvasView canvas={canvas} options={options} />
          {result.suggestions.length > 0 ? (
            <View style={styles.block}>
              <Heading level={3}>Podpowiedzi</Heading>
              {result.suggestions.map((item) => (
                <Txt key={item}>{item}</Txt>
              ))}
            </View>
          ) : null}
          {result.questions.length > 0 ? (
            <View style={styles.block}>
              <Heading level={3}>Pytania asystenta</Heading>
              {result.questions.map((item) => (
                <TextField
                  key={item.question}
                  label={item.question}
                  multiline
                  onChangeText={(value) => answer(item.question, value)}
                  value={drafts[item.question] ?? ""}
                />
              ))}
            </View>
          ) : null}
          {result.inspirations.length > 0 ? (
            <View style={styles.block}>
              <Heading level={3}>Co już działa w Małopolsce</Heading>
              <View role="list">
                {result.inspirations.map((item, index) => (
                  <InnovationRow
                    innovation={{
                      category: { name: "", slug: "" },
                      has_materials: false,
                      has_video: false,
                      lead: item.lead,
                      slug: item.slug,
                      title: item.title,
                    }}
                    key={item.slug}
                    last={index === result.inspirations.length - 1}
                    reason={item.why}
                  />
                ))}
              </View>
            </View>
          ) : null}
        </View>
      ) : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Button
        busy={busy}
        icon={result ? MessageCircleQuestion : Sparkles}
        label={(() => {
          if (busy) {
            return "Asystent myśli";
          }
          return result
            ? "Wyślij odpowiedzi asystentowi"
            : "Rozwiń pomysł z asystentem";
        })()}
        onPress={run}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    gap: space.md,
  },
  canvasRow: {
    borderRadius: radius.lg,
    gap: space.xs,
    padding: space.md,
  },
  list: {
    gap: space.sm,
  },
});
