import type { ReactNode, Ref } from "react";
import { ScrollView, StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { contentWidth, space } from "@/theme/tokens";

interface ScreenProps {
  children: ReactNode;
  width?: number;
}

export const Screen = function Screen({
  children,
  width = contentWidth,
  ref,
}: ScreenProps & { ref?: Ref<ScrollView> }) {
  const { colors, wide } = useTheme();
  return (
    <ScrollView
      contentContainerStyle={[
        styles.content,
        {
          paddingHorizontal: wide ? space.xxl : space.md,
          paddingTop: wide ? space.xl : space.md,
        },
      ]}
      keyboardShouldPersistTaps="handled"
      ref={ref}
      style={{ backgroundColor: colors.board }}
    >
      <View role="main" style={[styles.column, { maxWidth: width }]}>
        {children}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  column: {
    gap: space.lg,
    width: "100%",
  },
  content: {
    alignItems: "center",
    flexGrow: 1,
    paddingBottom: space.xxxl * 2,
  },
});
