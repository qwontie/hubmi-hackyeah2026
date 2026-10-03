const MARKS = /[̀-ͯ]/g;

const SIGNS = [
  "depresj",
  "samoboj",
  "zabic sie",
  "zabije sie",
  "odebrac sobie zycie",
  "skonczyc ze soba",
  "nie chce zyc",
  "nie chce mi sie zyc",
  "nie mam po co zyc",
  "nie mam sily zyc",
  "nie daje juz rady",
  "nie daje rady",
  "okalecz",
  "tne sie",
  "kryzys psychiczn",
  "zalamani",
  "atak paniki",
  "ataki paniki",
  "przemoc",
  "bije mnie",
  "bije mame",
  "bije dziec",
  "znecan",
  "zneca sie",
  "gwalt",
  "molestow",
  "boje sie o swoje zycie",
  "boje sie o zycie",
];

const fold = (text: string) =>
  text.toLowerCase().normalize("NFD").replace(MARKS, "").replaceAll("ł", "l");

export const isCrisis = (text: string) => {
  const folded = fold(text);
  return SIGNS.some((sign) => folded.includes(sign));
};
