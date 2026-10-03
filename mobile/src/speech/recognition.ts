import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from "expo-speech-recognition";
import { useCallback, useEffect, useRef, useState } from "react";

export interface Recognition {
  error: string | null;
  listening: boolean;
  start: () => void;
  stop: () => void;
  supported: boolean;
}

const PERMISSION_DENIED =
  "HubMi nie ma dostępu do mikrofonu lub rozpoznawania mowy. Zmień to w ustawieniach urządzenia.";

const ERRORS: Record<string, string> = {
  "audio-capture": "Nie znaleźliśmy mikrofonu. Sprawdź ustawienia urządzenia.",
  busy: "Mikrofon jest teraz zajęty. Spróbuj ponownie za chwilę.",
  interrupted: "Dyktowanie zostało przerwane. Spróbuj ponownie.",
  "language-not-supported": "To urządzenie nie obsługuje dyktowania po polsku.",
  network: "Dyktowanie wymaga internetu. Sprawdź połączenie.",
  "no-speech": "Nic nie usłyszeliśmy. Spróbuj jeszcze raz, mów wyraźnie.",
  "not-allowed": PERMISSION_DENIED,
  "service-not-allowed": "Rozpoznawanie mowy jest wyłączone na tym urządzeniu.",
  "speech-timeout": "Nic nie usłyszeliśmy. Spróbuj jeszcze raz.",
};

export const useRecognition = (onText: (text: string) => void): Recognition => {
  const callback = useRef(onText);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const supported = ExpoSpeechRecognitionModule.isRecognitionAvailable();

  useEffect(() => {
    callback.current = onText;
  }, [onText]);

  useEffect(
    () => () => {
      ExpoSpeechRecognitionModule.abort();
    },
    []
  );

  useSpeechRecognitionEvent("start", () => setListening(true));
  useSpeechRecognitionEvent("end", () => setListening(false));
  useSpeechRecognitionEvent("result", (event) => {
    if (!event.isFinal) {
      return;
    }
    const text = event.results[0]?.transcript.trim();
    if (text) {
      callback.current(text);
    }
  });
  useSpeechRecognitionEvent("error", (event) => {
    if (event.error === "aborted") {
      return;
    }
    setListening(false);
    setError(
      ERRORS[event.error] ??
        "Dyktowanie zostało przerwane. Spróbuj ponownie albo wpisz opis."
    );
  });

  const start = useCallback(() => {
    if (!supported) {
      return;
    }
    setError(null);
    ExpoSpeechRecognitionModule.requestPermissionsAsync()
      .then((permission) => {
        if (!permission.granted) {
          setError(PERMISSION_DENIED);
          return;
        }
        ExpoSpeechRecognitionModule.start({
          addsPunctuation: true,
          continuous: false,
          interimResults: false,
          lang: "pl-PL",
          maxAlternatives: 1,
        });
      })
      .catch(() =>
        setError("Nie udało się włączyć mikrofonu. Spróbuj ponownie.")
      );
  }, [supported]);

  const stop = useCallback(() => {
    ExpoSpeechRecognitionModule.stop();
  }, []);

  return { error, listening, start, stop, supported };
};
