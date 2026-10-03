import { StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

type Block =
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] };

const LIST_ITEM = /^\s*[-•]\s+/;
const PARAGRAPH_BREAK = /\n{2,}/;

export const parseBlocks = (source: string): Block[] => {
  const blocks: Block[] = [];
  for (const chunk of source.split(PARAGRAPH_BREAK)) {
    const lines = chunk
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    let list: string[] = [];
    let paragraph: string[] = [];
    const flushParagraph = () => {
      if (paragraph.length > 0) {
        blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
        paragraph = [];
      }
    };
    const flushList = () => {
      if (list.length > 0) {
        blocks.push({ items: list, kind: "list" });
        list = [];
      }
    };
    for (const line of lines) {
      if (LIST_ITEM.test(line)) {
        flushParagraph();
        list.push(line.replace(LIST_ITEM, ""));
      } else {
        flushList();
        paragraph.push(line);
      }
    }
    flushParagraph();
    flushList();
  }
  return blocks;
};

export const plainText = (source: string) =>
  parseBlocks(source)
    .map((block) =>
      block.kind === "paragraph" ? block.text : block.items.join(". ")
    )
    .join(" ");

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
