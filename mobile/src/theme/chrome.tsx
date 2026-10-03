import { useIsFocused } from "expo-router";
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type ChromeTone = "day" | "night" | "split";

interface ChromeValue {
  setTone: (tone: ChromeTone) => void;
  tone: ChromeTone;
}

const ChromeContext = createContext<ChromeValue>({
  setTone: () => undefined,
  tone: "day",
});

export function ChromeProvider({ children }: { children: ReactNode }) {
  const [tone, setTone] = useState<ChromeTone>("day");
  const value = useMemo(() => ({ setTone, tone }), [tone]);
  return (
    <ChromeContext.Provider value={value}>{children}</ChromeContext.Provider>
  );
}

export const useChromeTone = () => useContext(ChromeContext).tone;

export const useSetChromeTone = (tone: ChromeTone) => {
  const { setTone } = useContext(ChromeContext);
  const focused = useIsFocused();
  useEffect(() => {
    if (!focused) {
      return;
    }
    setTone(tone);
    return () => setTone("day");
  }, [tone, focused, setTone]);
};
