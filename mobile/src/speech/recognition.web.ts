import { useCallback, useEffect, useRef, useState } from "react";
import type { Recognition } from "./recognition";

interface SpeechAlternative {
  transcript: string;
}

interface SpeechResult {
  0: SpeechAlternative;
  isFinal: boolean;
}

interface SpeechResultEvent {
  resultIndex: number;
  results: ArrayLike<SpeechResult>;
}

interface SpeechErrorEvent {
  error: string;
}

interface SpeechRecognitionLike {
  abort: () => void;
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onend: (() => void) | null;
  onerror: ((event: SpeechErrorEvent) => void) | null;
  onresult: ((event: SpeechResultEvent) => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

const getCtor = (): SpeechRecognitionCtor | null => {
  if (typeof window === "undefined") {
    return null;
  }
  const scope = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
};

const ERRORS: Record<string, string> = {
  "audio-capture": "Nie znaleźliśmy mikrofonu. Sprawdź, czy jest podłączony.",
  network: "Dyktowanie wymaga internetu. Sprawdź połączenie.",
  "no-speech": "Nic nie usłyszeliśmy. Spróbuj jeszcze raz, mów wyraźnie.",
  "not-allowed":
    "Przeglądarka nie ma dostępu do mikrofonu. Zezwól na mikrofon w ustawieniach strony.",
  "service-not-allowed":
    "Przeglądarka nie pozwala na dyktowanie. Wpisz opis z klawiatury.",
};

export const useRecognition = (onText: (text: string) => void): Recognition => {
  const ctor = getCtor();
  const instance = useRef<SpeechRecognitionLike | null>(null);
  const callback = useRef(onText);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    callback.current = onText;
  }, [onText]);

  useEffect(
    () => () => {
      instance.current?.abort();
    },
    []
  );

  const stop = useCallback(() => {
    instance.current?.stop();
  }, []);

  const start = useCallback(() => {
    if (!ctor) {
      return;
    }
    instance.current?.abort();
    const recognition = new ctor();
    recognition.lang = "pl-PL";
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      let text = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result?.isFinal) {
          text += result[0].transcript;
        }
      }
      if (text.trim().length > 0) {
        callback.current(text.trim());
      }
    };
    recognition.onerror = (event) => {
      if (event.error === "aborted") {
        return;
      }
      setError(
        ERRORS[event.error] ??
          "Dyktowanie przerwało się. Spróbuj ponownie albo wpisz opis."
      );
    };
    recognition.onend = () => {
      setListening(false);
      if (instance.current === recognition) {
        instance.current = null;
      }
    };
    instance.current = recognition;
    setError(null);
    try {
      recognition.start();
      setListening(true);
    } catch {
      setError("Nie udało się włączyć mikrofonu. Spróbuj ponownie.");
    }
  }, [ctor]);

  return { error, listening, start, stop, supported: ctor !== null };
};
