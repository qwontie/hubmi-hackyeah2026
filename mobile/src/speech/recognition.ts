export interface Recognition {
  error: string | null;
  listening: boolean;
  start: () => void;
  stop: () => void;
  supported: boolean;
}

export const useRecognition = (
  _onText: (text: string) => void
): Recognition => ({
  error: null,
  listening: false,
  start: () => undefined,
  stop: () => undefined,
  supported: false,
});
