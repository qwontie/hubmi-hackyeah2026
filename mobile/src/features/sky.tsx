import { Animated, StyleSheet, useWindowDimensions, View } from "react-native";
import { useTheme } from "@/theme/settings";

const NARROW = { discs: [880, 600, 340], height: 344, tops: [48, 132, 232] };
const WIDE = { discs: [1900, 1240, 640], height: 300, tops: [60, 150, 240] };
const LIFT = [190, 210, 230];

export const skyHeight = (wide: boolean) => (wide ? WIDE : NARROW).height;

export function Sky({ rise }: { rise: Animated.Value }) {
  const { colors, wide } = useTheme();
  const { width } = useWindowDimensions();
  const shape = wide ? WIDE : NARROW;
  const tones = [colors.nightRise, colors.stamp, colors.horizon];
  return (
    <View
      aria-hidden
      pointerEvents="none"
      style={[styles.sky, { height: shape.height }]}
    >
      {shape.discs.map((size, index) => (
        <Animated.View
          key={size}
          style={{
            backgroundColor: tones[index],
            borderRadius: size / 2,
            height: size,
            left: (width - size) / 2,
            position: "absolute",
            top: shape.tops[index],
            transform: [
              {
                translateY: rise.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0, -(LIFT[index] ?? 0)],
                }),
              },
            ],
            width: size,
          }}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  sky: {
    bottom: 0,
    left: 0,
    position: "absolute",
    right: 0,
  },
});
