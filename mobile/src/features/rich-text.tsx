import { StyleSheet, View } from "react-native";
import { parseBlocks } from "@/lib/blocks";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

export function RichText({ source }: { source: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.wrap}>
      {parseBlocks(source).map((block, index) =>
        block.kind === "paragraph" ? (
          <Txt key={`p${index.toString()}`} style={styles.reading}>
            {block.text}
          </Txt>
        ) : (
          <View key={`l${index.toString()}`} role="list" style={styles.list}>
            {block.items.map((item, itemIndex) => (
              <View
                key={`i${itemIndex.toString()}`}
                role="listitem"
                style={styles.item}
              >
                <View
                  aria-hidden
                  style={[styles.bullet, { backgroundColor: colors.stamp }]}
                />
                <Txt style={styles.itemText}>{item}</Txt>
              </View>
            ))}
          </View>
        )
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  bullet: {
    borderRadius: 4,
    height: 7,
    marginTop: 11,
    width: 7,
  },
  item: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
  },
  itemText: {
    flex: 1,
    maxWidth: 660,
  },
  list: {
    gap: space.sm,
  },
  reading: {
    maxWidth: 680,
  },
  wrap: {
    gap: space.md,
  },
});
