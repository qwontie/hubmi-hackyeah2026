import { Platform } from "react-native";
import { useReadAloud } from "@/speech/read-aloud";
import { useSettings } from "@/theme/settings";
import { type TextScaleKey, textScales } from "@/theme/tokens";

const WHITESPACE = /\s+/g;

const mainText = () => {
  if (Platform.OS !== "web" || typeof document === "undefined") {
    return "";
  }
  const visible = Array.from(document.querySelectorAll("main")).filter(
    (element) => element.getClientRects().length > 0
  );
  const main = visible.at(-1);
  return (main?.innerText ?? "").replace(WHITESPACE, " ").trim();
};

export const useA11yControls = () => {
  const { settings, update } = useSettings();
  const reader = useReadAloud();
  const index = textScales.findIndex(
    (scale) => scale.key === settings.textScale
  );
  const current = textScales[index] ?? textScales[0];

  return {
    contrast: {
      label: settings.highContrast
        ? "Wysoki kontrast: włączony"
        : "Wysoki kontrast",
      on: settings.highContrast,
      toggle: () => update({ highContrast: !settings.highContrast }),
    },
    motion: {
      label: settings.reduceMotion ? "Mniej ruchu: włączone" : "Mniej ruchu",
      on: settings.reduceMotion,
      toggle: () => update({ reduceMotion: !settings.reduceMotion }),
    },
    read: {
      label: reader.speaking ? "Zatrzymaj czytanie" : "Przeczytaj stronę",
      on: reader.speaking,
      supported: reader.supported,
      toggle: (fallback?: string) => {
        const text = mainText() || fallback || "";
        if (reader.speaking || text.length > 0) {
          reader.toggle(text);
        }
      },
    },
    text: {
      cycle: () => {
        const next =
          textScales[(index + 1) % textScales.length] ?? textScales[0];
        update({ textScale: next.key });
      },
      label: `Tekst: ${current.label.toLowerCase()}`,
      options: textScales.map((scale) => ({
        label: scale.label,
        value: scale.key,
      })),
      set: (key: TextScaleKey) => update({ textScale: key }),
      value: current.key,
    },
  };
};
