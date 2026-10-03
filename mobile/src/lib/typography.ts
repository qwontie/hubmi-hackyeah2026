import { Children, isValidElement, type ReactNode } from "react";

const SHORT_WORD =
  /(^|[\s(„])([aiouwzAIOUWZ]|we|ze|na|do|od|po|za|że|by|to|ku)\s+/g;
const HYPHENATED = /(\p{L})-(\p{L})/gu;
const NUMBER_BEFORE_WORD = /(\d)\s+(?=\p{L})/gu;
const NO_BREAK_SPACE = " ";
const WORD_JOINER = "⁠";

const bindString = (text: string) =>
  text
    .replace(SHORT_WORD, `$1$2${NO_BREAK_SPACE}`)
    .replace(HYPHENATED, `$1-${WORD_JOINER}$2`)
    .replace(NUMBER_BEFORE_WORD, `$1${NO_BREAK_SPACE}`);

export const bindShortWords = (children: ReactNode): ReactNode => {
  if (typeof children === "string") {
    return bindString(children);
  }
  if (Array.isArray(children)) {
    return Children.map(children, (child) =>
      typeof child === "string" || !isValidElement(child)
        ? bindShortWords(child as ReactNode)
        : child
    );
  }
  return children;
};
