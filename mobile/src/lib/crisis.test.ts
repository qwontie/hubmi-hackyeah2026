import { describe, expect, test } from "bun:test";
import { isCrisis } from "@/lib/crisis";

const CRISIS = [
  "chcę się zabić",
  "chce sie zabic",
  "zabiję się",
  "mąż mnie bije",
  "maz mnie bije",
  "bije mnie partner",
  "ojciec bił mnie i mamę",
  "chcę umrzeć",
  "wolałabym umrzeć",
  "nie chcę już żyć",
  "nie chce juz zyc",
  "żyć już nie chcę",
  "chcę skończyć ze sobą",
  "skończę ze sobą",
  "myślę o samobójstwie",
  "samobojstwo",
  "boję się męża",
  "boje sie meza",
  "boję się wracać do domu",
  "doświadczam przemocy w domu",
  "przemoc",
  "nie daję już rady",
  "tnę się",
  "chcę sobie zrobić krzywdę",
  "mam ataki paniki",
  "KTOŚ MNIE BIJE",
  "nie mam po co żyć",
  "nie chce mi się żyć",
  "chcę odebrać sobie życie",
  "ojczym znęca się nad nami",
  "boję się o swoje życie",
  "przeżywam kryzys psychiczny",
  "molestowanie w pracy",
];

const CALM = [
  "brakuje opieki dla mamy po udarze",
  "nie mam pieniędzy na życie",
  "nie mam jak dojechać do lekarza",
  "zabierz mnie na zakupy",
  "kupiłem bilet dla nas",
  "boję się, że nie zdążę z wnioskiem",
  "Mąż nie pracuje. Bije się z myślami, co dalej",
  "",
];

describe("isCrisis", () => {
  test.each(CRISIS)("shows help for %p", (text) => {
    expect(isCrisis(text)).toBe(true);
  });

  test.each(CALM)("stays quiet for %p", (text) => {
    expect(isCrisis(text)).toBe(false);
  });
});
