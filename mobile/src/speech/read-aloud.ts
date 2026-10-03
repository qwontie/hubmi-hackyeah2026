import { speak, stop as stopSpeech } from "expo-speech";
import { useCallback, useEffect, useState } from "react";
import { Platform } from "react-native";

const supported =
  Platform.OS !== "web" ||
  (typeof window !== "undefined" && "speechSynthesis" in window);

let activeOwner: symbol | null = null;
const listeners = new Set<() => void>();

const notify = () => {
  for (const listener of listeners) {
    listener();
  }
};

const stop = () => {
  activeOwner = null;
  stopSpeech();
  notify();
};

export const useReadAloud = () => {
  const [owner] = useState(() => Symbol("reader"));
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    const listener = () => setSpeaking(activeOwner === owner);
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
      if (activeOwner === owner) {
        stop();
      }
    };
  }, [owner]);

  const toggle = useCallback(
    (text: string) => {
      if (activeOwner === owner) {
        stop();
        return;
      }
      stopSpeech();
      activeOwner = owner;
      notify();
      const finish = () => {
        if (activeOwner === owner) {
          activeOwner = null;
          notify();
        }
      };
      speak(text, {
        language: "pl-PL",
        onDone: finish,
        onError: finish,
        onStopped: finish,
        rate: 0.92,
      });
    },
    [owner]
  );

  return { speaking, supported, toggle };
};
