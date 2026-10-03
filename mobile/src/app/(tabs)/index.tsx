import { useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { EntryChoice } from "@/features/entry-choice";
import { MatchResults } from "@/features/match-results";
import { ProblemComposer } from "@/features/problem-composer";
import { Sky, skyHeight } from "@/features/sky";
import { useMatch } from "@/hooks/use-match";
import { useSetChromeTone } from "@/theme/chrome";
import { useTheme } from "@/theme/settings";
import { motion, space, tabBarSpace } from "@/theme/tokens";
import { nightAttr } from "@/ui/night";
import { nativeDriver } from "@/ui/rise";
import { BackPill, WIDE_TOP } from "@/ui/screen";
import { AccessButton, Brand } from "@/ui/shell";
import { Heading } from "@/ui/text";

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

const chromeTone = (done: boolean, dawning: boolean, wide: boolean) => {
  if (!done || dawning) {
    return "night" as const;
  }
  return wide ? ("split" as const) : ("day" as const);
};

export default function MatchScreen() {
  const { colors, wide, roomy, type, reduceMotion } = useTheme();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const match = useMatch();
  const { inputRef, loading, powiat, reset, resultsRef, state, text } = match;
  const [chosen, setChosen] = useState(false);
  const done = state.kind === "done";
  const asking =
    chosen || powiat !== "" || text.length > 0 || state.kind !== "idle";
  const { dawn, dawning, rise } = useDawn(loading, done);
  useSetChromeTone(chromeTone(done, dawning, wide));

  useEffect(() => {
    if (chosen) {
      inputRef.current?.focus();
    }
  }, [chosen, inputRef]);

  const leave = () => {
    setChosen(false);
    reset();
  };

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

  const display = wide
    ? Math.round(type.display * (roomy ? 2 : 1.6))
    : Math.min(type.display, Math.floor((width - 44) / 6.5));

  return (
    <View
      role="main"
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
          wide && styles.contentWide,
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <View
          style={[
            styles.column,
            wide && (asking ? styles.columnAsk : styles.columnWide),
            roomy && (asking ? styles.columnAskRoomy : styles.columnRoomy),
          ]}
        >
          {wide ? null : (
            <View style={styles.top}>
              <Brand night />
              <AccessButton night />
            </View>
          )}
          {asking ? (
            <>
              <BackPill label="Wróć" night onPress={leave} />
              <ProblemComposer match={match} />
            </>
          ) : (
            <>
              <Heading
                level={1}
                night
                style={[
                  styles.question,
                  {
                    fontSize: display,
                    letterSpacing: display * -0.035,
                    lineHeight: Math.round(display * 1.04),
                  },
                  wide && styles.center,
                ]}
              >
                Z czym przychodzisz?
              </Heading>
              <EntryChoice onProblem={() => setChosen(true)} />
            </>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  center: {
    textAlign: "center",
  },
  column: {
    gap: space.lg + 2,
    width: "100%",
  },
  columnAsk: {
    alignSelf: "center",
    gap: space.xl,
    maxWidth: 1240,
  },
  columnAskRoomy: {
    maxWidth: 1560,
  },
  columnRoomy: {
    maxWidth: 1080,
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
  contentWide: {
    paddingHorizontal: 40,
  },
  dawn: {
    overflow: "hidden",
  },
  question: {
    marginTop: space.md,
  },
  root: {
    flex: 1,
    overflow: "hidden",
  },
  top: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
});
