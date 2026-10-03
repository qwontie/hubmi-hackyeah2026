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

export const useSetChromeTone = (tone: ChromeTone, active = true) => {
  const { setTone } = useContext(ChromeContext);
  useEffect(() => {
    if (!active) {
      return;
    }
    setTone(tone);
    return () => setTone("day");
  }, [tone, active, setTone]);
};
