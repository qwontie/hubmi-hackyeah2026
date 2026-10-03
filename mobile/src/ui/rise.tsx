import { type ReactNode, useEffect, useRef } from "react";
import {
  Animated,
  Easing,
  Platform,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { useTheme } from "@/theme/settings";
import { motion } from "@/theme/tokens";

export const nativeDriver = Platform.OS !== "web";

interface RiseProps {
  children: ReactNode;
  delay?: number;
  distance?: number;
  style?: StyleProp<ViewStyle>;
}

export function Rise({ children, delay = 0, distance = 18, style }: RiseProps) {
  const { reduceMotion } = useTheme();
  const value = useRef(new Animated.Value(reduceMotion ? 1 : 0)).current;

  useEffect(() => {
    if (reduceMotion) {
      value.setValue(1);
      return;
    }
    const animation = Animated.timing(value, {
      delay,
      duration: motion.rise,
      easing: Easing.bezier(0.16, 1, 0.3, 1),
      toValue: 1,
      useNativeDriver: nativeDriver,
    });
    animation.start();
    return () => animation.stop();
  }, [value, delay, reduceMotion]);

  return (
    <Animated.View
      style={[
        style,
        {
          opacity: value,
          transform: [
            {
              translateY: value.interpolate({
                inputRange: [0, 1],
                outputRange: [distance, 0],
              }),
            },
          ],
        },
      ]}
    >
      {children}
    </Animated.View>
  );
}
