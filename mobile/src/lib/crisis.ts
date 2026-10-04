const MARKS = /[̀-ͯ]/g;
const SENTENCES = /[.!?;\n]+/;
const WORD_BREAK = /[^a-z0-9]+/;
const NEAR = 7;

const ANYWHERE = [
  "samoboj*",
  "depresj*",
  "przemoc*",
  "okalecz*",
  "samookalecz*",
  "zalaman*",
  "zneca*",
  "gwalt*",
  "gwalc*",
  "zgwalc*",
  "molest*",
  "umrzec",
  "umre",
];

const TOGETHER = [
  [
    ["zabic", "zabij*", "zabil*"],
    ["sie", "mnie"],
  ],
  [["odebrac", "odbiore"], ["sobie"], ["zyci*"]],
  [["skoncz*"], ["ze"], ["soba"]],
  [["nie"], ["chc*", "moge", "mam", "umiem", "potrafie", "warto"], ["zyc"]],
  [["nie"], ["daje"], ["rady"]],
  [["tne", "ciac"], ["sie"]],
  [["kryzys*"], ["psychiczn*"]],
  [["atak*"], ["panik*"]],
  [
    ["bij*", "bil", "bila", "bili", "pobil*"],
    [
      "mnie",
      "nas",
      "mame",
      "matke",
      "dzieci*",
      "dziecko",
      "zone",
      "corke",
      "syna",
      "brata",
      "siostre",
    ],
  ],
  [["krzywd*"], ["sobie", "mi", "mnie"]],
  [
    ["boje", "boimy", "boi"],
    ["sie"],
    [
      "meza",
      "zony",
      "partner*",
      "ojca",
      "taty",
      "ojczyma",
      "matki",
      "mamy",
      "chlopaka",
      "dziewczyny",
      "syna",
      "corki",
      "brata",
      "wracac",
      "zycie",
    ],
  ],
];

const fold = (text: string) =>
  text.toLowerCase().normalize("NFD").replace(MARKS, "").replaceAll("ł", "l");

const fits = (word: string, pattern: string) =>
  pattern.endsWith("*")
    ? word.startsWith(pattern.slice(0, -1))
    : word === pattern;

const fitsAny = (word: string, slot: string[]) =>
  slot.some((pattern) => fits(word, pattern));

const near = (words: string[], slots: string[][]) =>
  words.some((_, start) => {
    const span = words.slice(start, start + NEAR);
    return slots.every((slot) => span.some((word) => fitsAny(word, slot)));
  });

export const isCrisis = (text: string) =>
  fold(text)
    .split(SENTENCES)
    .some((sentence) => {
      const words = sentence.split(WORD_BREAK).filter(Boolean);
      return (
        words.some((word) => ANYWHERE.some((sign) => fits(word, sign))) ||
        TOGETHER.some((slots) => near(words, slots))
      );
    });
