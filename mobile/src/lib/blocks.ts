export type Block =
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
