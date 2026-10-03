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

const chromeTone = (
  asking: boolean,
  done: boolean,
  dawning: boolean,
  wide: boolean
) => {
  const lit = wide ? ("split" as const) : ("day" as const);
  if (!asking) {
    return lit;
  }
  return done && !dawning ? lit : ("night" as const);
};

export default function MatchScreen() {
  const { colors, wide, roomy, reduceMotion } = useTheme();
  const insets = useSafeAreaInsets();
  const match = useMatch();
  const { inputRef, loading, powiat, reset, resultsRef, state, text } = match;
  const [chosen, setChosen] = useState(false);
  const done = state.kind === "done";
  const asking =
    chosen || powiat !== "" || text.length > 0 || state.kind !== "idle";
  const { dawn, dawning, rise } = useDawn(loading, done);
  useSetChromeTone(chromeTone(asking, done, dawning, wide));

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

  if (!asking) {
    return (
      <ScrollView
        contentContainerStyle={styles.fill}
        role="main"
        style={{ backgroundColor: colors.night }}
      >
        <EntryChoice
          onProblem={() => setChosen(true)}
          top={
            wide ? null : (
              <View style={styles.top}>
                <Brand night />
                <AccessButton night />
              </View>
            )
          }
        />
      </ScrollView>
    );
  }

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
            wide && styles.columnAsk,
            roomy && styles.columnAskRoomy,
          ]}
        >
          {wide ? null : (
            <View style={styles.top}>
              <Brand night />
              <AccessButton night />
            </View>
          )}
          <BackPill label="Wróć" night onPress={leave} />
          <ProblemComposer match={match} />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  column: {
    gap: space.lg + 2,
    width: "100%",
  },
  columnAsk: {
    gap: space.xl,
    maxWidth: 1360,
  },
  columnAskRoomy: {
    maxWidth: 1760,
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
  fill: {
    flexGrow: 1,
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
