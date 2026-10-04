import { CircleAlert, Mic, Square } from "lucide-react-native";
import { useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  type TextStyle,
  useWindowDimensions,
  View,
} from "react-native";
import { TEXT_MAX } from "@/config";
import { charactersLeft, type useMatch } from "@/hooks/use-match";
import type { Recognition } from "@/speech/recognition";
import { useTheme } from "@/theme/settings";
import { fonts, minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Notice } from "@/ui/notice";
import { Txt } from "@/ui/text";

type Match = ReturnType<typeof useMatch>;

const TITLE_ID = "problem-title";
const ERROR_ID = "problem-error";
const QUESTION = "Opowiedz, co się dzieje.";

const web = Platform.OS === "web";

const ease = (
  web
    ? {
        transitionDuration: "320ms",
        transitionProperty: "font-size, line-height, color",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }
    : {}
) as TextStyle;

const wordsSize = (length: number, wide: boolean, factor: number) => {
  const steps = wide ? [56, 44, 34, 26] : [32, 27, 23, 20];
  const limits = [60, 140, 260];
  const index = limits.findIndex((limit) => length <= limit);
  const size = steps[index === -1 ? 3 : index] ?? 20;
  return Math.round(size * factor);
};

function Voice({ recognition }: { recognition: Recognition }) {
  const { borderWidth, colors, highContrast, reduceMotion } = useTheme();
  if (!(recognition.supported || web)) {
    return (
      <View style={styles.voice}>
        <Mic aria-hidden color={colors.inkSoft} size={22} />
        <Txt tone="soft" variant="small">
          Można dyktować z klawiatury
        </Txt>
      </View>
    );
  }
  const { listening } = recognition;
  const Icon = listening ? Square : Mic;
  return (
    <Pressable
      aria-pressed={listening}
      onPress={listening ? recognition.stop : recognition.start}
      role="button"
      style={({ pressed }) => [
        styles.voice,
        { transform: [{ scale: pressed && !reduceMotion ? 0.96 : 1 }] },
      ]}
    >
      <View
        style={[
          styles.voiceDot,
          {
            backgroundColor: listening ? colors.stamp : colors.tone,
            borderColor: colors.ink,
            borderWidth: highContrast ? borderWidth : 0,
          },
        ]}
      >
        <Icon
          aria-hidden
          color={listening ? colors.onStamp : colors.stamp}
          size={listening ? 20 : 26}
          strokeWidth={2.2}
        />
      </View>
      <Txt tone="stamp" variant="label" weight="600">
        {listening ? "Zakończ dyktowanie" : "Powiedz"}
      </Txt>
    </Pressable>
  );
}

function Feedback({ match }: { match: Match }) {
  const { colors } = useTheme();
  const { fieldError, recognition, state, submit, text } = match;
  const left = charactersLeft(text.length);
  return (
    <View aria-live="polite" style={styles.feedback}>
      {left ? (
        <Txt
          tone={left.over ? "bad" : "soft"}
          variant="small"
          weight={left.over ? "600" : "400"}
        >
          {left.text}
        </Txt>
      ) : null}
      {fieldError ? (
        <View style={styles.error}>
          <CircleAlert aria-hidden color={colors.bad} size={24} />
          <Txt nativeID={ERROR_ID} style={styles.grow} weight="600">
            {fieldError}
          </Txt>
        </View>
      ) : null}
      {recognition.listening ? (
        <Txt weight="500">
          Słucham. Mów po polsku, tekst pojawi się na ekranie.
        </Txt>
      ) : null}
      {recognition.error ? <Txt weight="600">{recognition.error}</Txt> : null}
      {state.kind === "error" ? (
        <Notice tone="error">
          <View style={styles.errorBody}>
            <Txt>{state.message}</Txt>
            {state.retryable ? (
              <Button label="Spróbuj ponownie" onPress={submit} />
            ) : null}
          </View>
        </Notice>
      ) : null}
    </View>
  );
}

function Words({ match }: { match: Match }) {
  const { colors, wide, roomy, type } = useTheme();
  const { width } = useWindowDimensions();
  const [focused, setFocused] = useState(false);
  const [height, setHeight] = useState(0);
  const { fieldError, inputRef, loading, setText, submit, text } = match;
  const typed = text.length > 0;
  const factor = (type.body / 19) * (roomy ? 1.25 : 1);
  const display = wide
    ? Math.round(64 * factor)
    : Math.min(type.display, Math.floor((width - 44) / 6.5));
  const questionSize = typed ? type.lead : display;
  const hintSize = wide ? type.h3 : type.lead;
  const size = typed ? wordsSize(text.length, wide, factor) : hintSize;
  const line = Math.round(size * (typed ? 1.22 : 1.4));
  const floor = Math.round(wordsSize(0, wide, factor) * 1.22) * 2 + space.lg;
  return (
    <View style={styles.words}>
      <Text
        aria-level={1}
        maxFontSizeMultiplier={1.3}
        nativeID={TITLE_ID}
        role="heading"
        style={[
          ease,
          {
            color: typed ? colors.inkSoft : colors.ink,
            fontFamily: typed ? fonts["500"] : fonts["600"],
            fontSize: questionSize,
            letterSpacing: typed ? 0 : questionSize * -0.035,
            lineHeight: Math.round(questionSize * (typed ? 1.4 : 1.04)),
          },
        ]}
      >
        {QUESTION}
      </Text>
      <TextInput
        accessibilityLabel="Opis problemu"
        aria-describedby={fieldError ? ERROR_ID : undefined}
        aria-invalid={fieldError ? true : undefined}
        aria-labelledby={TITLE_ID}
        editable={!loading}
        maxFontSizeMultiplier={1.5}
        maxLength={TEXT_MAX + 200}
        multiline
        onBlur={() => setFocused(false)}
        onChangeText={setText}
        onContentSizeChange={(event) => {
          const next = Math.ceil(event.nativeEvent.contentSize.height);
          setHeight((current) => (next > current ? next : current));
        }}
        onFocus={() => setFocused(true)}
        onKeyPress={(event) => {
          const native = event.nativeEvent as {
            key: string;
            shiftKey?: boolean;
          };
          if (web && native.key === "Enter" && !native.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        placeholder={
          "Na przykład: mama z\u00a0demencją wychodzi z\u00a0domu i\u00a0się gubi."
        }
        placeholderTextColor={colors.inkSoft}
        ref={inputRef}
        selectionColor={colors.horizon}
        style={[
          styles.input,
          {
            borderBottomColor: focused ? colors.ring : colors.ruleStrong,
            borderBottomWidth: focused ? 3 : 2,
            color: colors.ink,
            fontFamily: typed ? fonts["600"] : fonts["400"],
            fontSize: size,
            height: Math.max(floor, height),
            letterSpacing: typed ? size * -0.025 : 0,
            lineHeight: line,
            paddingBottom: focused ? space.md - 1 : space.md,
          },
        ]}
        value={text}
      />
    </View>
  );
}

export function ProblemComposer({ match }: { match: Match }) {
  const { wide } = useTheme();
  const { blocked, loading, recognition, submit } = match;

  return (
    <View style={styles.main}>
      <Words match={match} />
      <View aria-live="polite">
        {loading ? (
          <Txt tone="soft" variant="lead">
            Szukamy w bibliotece ROPS. To trwa zwykle kilka sekund.
          </Txt>
        ) : null}
      </View>
      <Feedback match={match} />
      <View style={styles.actions}>
        <Button
          busy={loading}
          disabled={blocked}
          fill={!wide}
          label={loading ? "Szukam rozwiązań" : "Znajdź rozwiązania"}
          onPress={submit}
          size="large"
          style={wide ? styles.submit : undefined}
          variant="primary"
        />
        <Voice recognition={recognition} />
      </View>
      {wide && web ? (
        <Txt tone="soft" variant="small">
          Enter szuka. Shift i Enter to nowa linia.
        </Txt>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.lg,
  },
  error: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.sm + 2,
  },
  errorBody: {
    gap: space.md,
  },
  feedback: {
    gap: space.sm,
  },
  grow: {
    flex: 1,
  },
  input: {
    paddingHorizontal: 0,
    paddingTop: space.xs,
    textAlignVertical: "top",
    ...(web ? ({ outlineStyle: "none" } as object) : {}),
  },
  main: {
    gap: space.lg + 2,
  },
  submit: {
    minWidth: 300,
  },
  voice: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.sm + 2,
    minHeight: minTarget + 8,
    paddingRight: space.md,
  },
  voiceDot: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: minTarget + 8,
    justifyContent: "center",
    width: minTarget + 8,
  },
  words: {
    gap: space.md,
  },
});
