import { Link } from "expo-router";
import { CircleAlert, Mic, Square } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "@/api/client";
import type { Category } from "@/api/types";
import { TEXT_MAX } from "@/config";
import { CategoryIcon } from "@/features/category-icon";
import { MatchResults } from "@/features/match-results";
import { Sky, skyHeight } from "@/features/sky";
import { charactersLeft, useMatch } from "@/hooks/use-match";
import { usePowiats } from "@/hooks/use-powiats";
import { useResource } from "@/hooks/use-resource";
import type { Recognition } from "@/speech/recognition";
import { useSetChromeTone } from "@/theme/chrome";
import { useTheme } from "@/theme/settings";
import {
  fonts,
  minTarget,
  motion,
  radius,
  space,
  tabBarSpace,
} from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Glass } from "@/ui/glass";
import { nightAttr } from "@/ui/night";
import { Notice } from "@/ui/notice";
import { nativeDriver } from "@/ui/rise";
import { WIDE_TOP } from "@/ui/screen";
import { Select } from "@/ui/select";
import { AccessButton, Brand } from "@/ui/shell";
import { Heading, Txt } from "@/ui/text";

const TITLE_ID = "problem-title";
const ERROR_ID = "problem-error";
const WASH = "rgba(252, 252, 255, 0.14)";

const loadCategories = (_key: string, signal: AbortSignal) =>
  api.categories(signal);

function Voice({ recognition }: { recognition: Recognition }) {
  const { colors, reduceMotion } = useTheme();
  if (!recognition.supported) {
    return null;
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
          { backgroundColor: listening ? colors.onNight : WASH },
        ]}
      >
        <Icon
          aria-hidden
          color={listening ? colors.night : colors.onNight}
          size={listening ? 20 : 24}
          strokeWidth={2.2}
        />
      </View>
      <Txt tone="onNight" variant="label" weight="600">
        {listening ? "Zakończ dyktowanie" : "Powiedz"}
      </Txt>
    </Pressable>
  );
}

function Topics({ categories }: { categories: Category[] }) {
  const { colors, wide, highContrast } = useTheme();
  if (categories.length === 0) {
    return null;
  }
  const chips = categories.map((category) => (
    <Link
      asChild
      href={{ params: { kategoria: category.slug }, pathname: "/biblioteka" }}
      key={category.slug}
    >
      <Pressable
        role="link"
        style={StyleSheet.flatten([
          styles.chip,
          {
            backgroundColor: highContrast ? colors.nightDeep : WASH,
            borderColor: colors.glassNightEdge,
          },
        ])}
      >
        <CategoryIcon color={colors.onNight} size={22} slug={category.slug} />
        <Txt tone="onNight" variant="label" weight="500">
          {category.name}
        </Txt>
      </Pressable>
    </Link>
  ));
  return (
    <View style={styles.topics}>
      <Txt
        style={wide ? styles.center : undefined}
        tone="onNightSoft"
        variant="label"
        weight="600"
      >
        Albo wybierz temat
      </Txt>
      {wide ? (
        <View style={styles.chipsWide}>{chips}</View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.chips}
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.chipsBleed}
        >
          {chips}
        </ScrollView>
      )}
    </View>
  );
}

function Dawn({ dawn, rise }: { dawn: Animated.Value; rise: Animated.Value }) {
  const { colors, wide } = useTheme();
  const { width, height } = useWindowDimensions();
  const reach = Math.hypot(width, height);
  const sunY = height - skyHeight(wide) + 60;
  return (
    <Animated.View
      aria-hidden
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        styles.dawn,
        {
          backgroundColor: colors.night,
          opacity: dawn.interpolate({
            inputRange: [0, 0.82, 1],
            outputRange: [1, 1, 0],
          }),
        },
      ]}
    >
      <Sky rise={rise} />
      <Animated.View
        style={{
          backgroundColor: colors.ground,
          borderRadius: reach,
          height: reach * 2,
          left: width / 2 - reach,
          position: "absolute",
          top: sunY - reach,
          transform: [
            {
              scale: dawn.interpolate({
                inputRange: [0, 0.82],
                outputRange: [0.04, 1],
              }),
            },
          ],
          width: reach * 2,
        }}
      />
    </Animated.View>
  );
}

const useDawn = (loading: boolean, done: boolean) => {
  const { reduceMotion } = useTheme();
  const [dawned, setDawned] = useState(false);
  const rise = useRef(new Animated.Value(0)).current;
  const dawn = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (reduceMotion) {
      return;
    }
    const lifted = loading || done;
    const animation = Animated.timing(rise, {
      duration: lifted ? motion.sunrise : motion.settle,
      easing: Easing.bezier(0.45, 0, 0.2, 1),
      toValue: lifted ? 1 : 0,
      useNativeDriver: nativeDriver,
    });
    animation.start();
    return () => animation.stop();
  }, [loading, done, reduceMotion, rise]);

  useEffect(() => {
    if (!done) {
      dawn.setValue(0);
      setDawned(false);
      return;
    }
    if (reduceMotion) {
      setDawned(true);
      return;
    }
    const animation = Animated.timing(dawn, {
      duration: motion.dawn,
      easing: Easing.bezier(0.5, 0, 0.15, 1),
      toValue: 1,
      useNativeDriver: nativeDriver,
    });
    animation.start(({ finished }) => {
      if (finished) {
        setDawned(true);
      }
    });
    return () => animation.stop();
  }, [done, reduceMotion, dawn]);

  return { dawn, dawning: done && !dawned && !reduceMotion, rise };
};

type Match = ReturnType<typeof useMatch>;

function ProblemField({ match }: { match: Match }) {
  const { colors, wide, type, lineHeight } = useTheme();
  const [focused, setFocused] = useState(false);
  const { fieldError, inputRef, loading, recognition, setText, text } = match;
  const left = charactersLeft(text.length);
  const inputSize = wide ? type.h3 : type.lead;
  return (
    <View
      style={[
        styles.fieldRing,
        { borderColor: focused ? colors.onNight : "transparent" },
      ]}
    >
      <Glass night style={styles.field}>
        <TextInput
          accessibilityLabel="Opis problemu"
          aria-describedby={fieldError ? ERROR_ID : undefined}
          aria-invalid={fieldError ? true : undefined}
          aria-labelledby={TITLE_ID}
          editable={!loading}
          maxLength={TEXT_MAX + 200}
          multiline
          onBlur={() => setFocused(false)}
          onChangeText={setText}
          onFocus={() => setFocused(true)}
          placeholder="Na przykład: mama z demencją wychodzi z domu i się gubi."
          placeholderTextColor={colors.onNightSoft}
          ref={inputRef}
          selectionColor={colors.onNightSoft}
          style={[
            styles.input,
            {
              color: colors.onNight,
              fontFamily: fonts["400"],
              fontSize: inputSize,
              lineHeight: lineHeight(inputSize),
              minHeight: lineHeight(inputSize) * 3 + space.md,
            },
          ]}
          value={text}
        />
        <View style={styles.fieldFoot}>
          <Voice recognition={recognition} />
          {left ? (
            <Txt
              aria-live="polite"
              tone={left.over ? "onNight" : "onNightSoft"}
              variant="small"
              weight={left.over ? "600" : "400"}
            >
              {left.text}
            </Txt>
          ) : null}
        </View>
      </Glass>
    </View>
  );
}

function FieldFeedback({ match }: { match: Match }) {
  const { colors } = useTheme();
  const { fieldError, recognition } = match;
  return (
    <View aria-live="polite">
      {fieldError ? (
        <View style={styles.error}>
          <CircleAlert aria-hidden color={colors.onNight} size={24} />
          <Txt
            nativeID={ERROR_ID}
            style={styles.errorText}
            tone="onNight"
            weight="600"
          >
            {fieldError}
          </Txt>
        </View>
      ) : null}
      {recognition.listening ? (
        <Txt tone="onNight" weight="500">
          Słucham. Proszę mówić po polsku, tekst pojawi się w polu.
        </Txt>
      ) : null}
      {recognition.error ? (
        <Txt tone="onNight" weight="600">
          {recognition.error}
        </Txt>
      ) : null}
    </View>
  );
}

function Intro({ loading }: { loading: boolean }) {
  const { wide, type } = useTheme();
  const display = wide ? Math.round(type.display * 1.6) : type.display;
  return (
    <View style={styles.intro}>
      <Heading
        level={1}
        nativeID={TITLE_ID}
        night
        style={[
          {
            fontSize: display,
            letterSpacing: display * -0.035,
            lineHeight: Math.round(display * 1.04),
          },
          wide && styles.center,
        ]}
      >
        {wide
          ? "Proszę opowiedzieć,\nco się dzieje."
          : "Proszę opowiedzieć, co\u00a0się\u00a0dzieje."}
      </Heading>
      <View aria-live="polite">
        <Txt
          style={wide ? styles.center : undefined}
          tone="onNightSoft"
          variant="lead"
        >
          {loading
            ? "Szukamy w bibliotece ROPS. To trwa zwykle kilka sekund."
            : "Znajdziemy rozwiązania, które już działają w Małopolsce."}
        </Txt>
      </View>
    </View>
  );
}

function Actions({ match }: { match: Match }) {
  const { wide } = useTheme();
  const powiats = usePowiats();
  const { blocked, loading, powiat, setPowiat, state, submit } = match;
  return (
    <>
      <View style={[styles.actions, wide && styles.actionsWide]}>
        {powiats.options.length > 0 ? (
          <View style={wide ? styles.powiatWide : undefined}>
            <Select
              emptyLabel="Nie wybieram"
              label="Powiat"
              night
              onChange={setPowiat}
              optional
              options={powiats.options}
              value={powiat}
            />
          </View>
        ) : null}
        <Button
          busy={loading}
          disabled={blocked}
          fill={!wide}
          label={loading ? "Szukam rozwiązań" : "Znajdź rozwiązania"}
          onPress={submit}
          size="large"
          style={wide ? styles.submitWide : undefined}
          variant="light"
        />
      </View>
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
    </>
  );
}

const chromeTone = (done: boolean, dawning: boolean, wide: boolean) => {
  if (!done || dawning) {
    return "night" as const;
  }
  return wide ? ("split" as const) : ("day" as const);
};

export default function MatchScreen() {
  const { colors, wide, reduceMotion } = useTheme();
  const insets = useSafeAreaInsets();
  const categories = useResource("categories", loadCategories);
  const match = useMatch();
  const { loading, reset, resultsRef, state, text } = match;
  const done = state.kind === "done";
  const { dawn, dawning, rise } = useDawn(loading, done);
  useSetChromeTone(chromeTone(done, dawning, wide));

  if (state.kind === "done") {
    return (
      <View style={[styles.root, { backgroundColor: colors.ground }]}>
        <MatchResults
          at={state.at}
          key={state.response.need.id}
          onReset={reset}
          response={state.response}
          settle={reduceMotion ? 0 : motion.dawn - 200}
          text={text.trim()}
          titleRef={resultsRef}
        />
        {dawning ? <Dawn dawn={dawn} rise={rise} /> : null}
      </View>
    );
  }

  return (
    <View
      style={[styles.root, { backgroundColor: colors.night }]}
      {...nightAttr(true)}
    >
      <Sky rise={rise} />
      <ScrollView
        contentContainerStyle={[
          styles.content,
          {
            paddingBottom: tabBarSpace + insets.bottom + space.lg,
            paddingTop: wide ? WIDE_TOP + space.lg : insets.top + space.sm,
          },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <View role="main" style={[styles.column, wide && styles.columnWide]}>
          {wide ? null : (
            <View style={styles.top}>
              <Brand night />
              <AccessButton night />
            </View>
          )}
          <Intro loading={loading} />
          <ProblemField match={match} />
          <FieldFeedback match={match} />
          <Actions match={match} />
          <Topics
            categories={
              categories.state.kind === "done" ? categories.state.data : []
            }
          />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  actions: {
    gap: space.lg,
  },
  actionsWide: {
    alignItems: "flex-end",
    flexDirection: "row",
    justifyContent: "center",
  },
  center: {
    textAlign: "center",
  },
  chip: {
    alignItems: "center",
    borderRadius: radius.pill,
    borderWidth: 1,
    flexDirection: "row",
    gap: space.sm + 2,
    minHeight: minTarget + 4,
    paddingHorizontal: space.lg + 2,
  },
  chips: {
    gap: space.sm + 2,
    paddingHorizontal: space.xl - 2,
  },
  chipsBleed: {
    marginHorizontal: -(space.xl - 2),
  },
  chipsWide: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm + 2,
    justifyContent: "center",
  },
  column: {
    gap: space.lg + 2,
    width: "100%",
  },
  columnWide: {
    alignSelf: "center",
    gap: space.xl + 4,
    maxWidth: 860,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: space.xl - 2,
  },
  dawn: {
    overflow: "hidden",
  },
  error: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.sm + 2,
  },
  errorBody: {
    gap: space.md,
  },
  errorText: {
    flex: 1,
  },
  field: {
    borderRadius: radius.field,
    paddingBottom: space.sm,
    paddingHorizontal: space.sm,
    paddingTop: space.sm,
  },
  fieldFoot: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    paddingRight: space.md,
  },
  fieldRing: {
    borderRadius: radius.field + 4,
    borderWidth: 2,
    margin: -4,
    padding: 2,
  },
  input: {
    paddingHorizontal: space.md + 2,
    paddingVertical: space.md,
    textAlignVertical: "top",
  },
  intro: {
    gap: space.md + 2,
    marginTop: space.md,
  },
  powiatWide: {
    width: 320,
  },
  root: {
    flex: 1,
  },
  submitWide: {
    minWidth: 300,
  },
  top: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  topics: {
    gap: space.md,
    marginTop: space.sm,
  },
  voice: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.sm + 2,
    minHeight: minTarget + 4,
    paddingRight: space.md,
  },
  voiceDot: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: minTarget + 4,
    justifyContent: "center",
    width: minTarget + 4,
  },
});
