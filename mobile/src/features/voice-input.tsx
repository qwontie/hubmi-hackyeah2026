import { Mic, MicOff } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { Recognition } from "@/speech/recognition";
import { space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Txt } from "@/ui/text";

export function VoiceInput({ recognition }: { recognition: Recognition }) {
  if (!recognition.supported) {
    return null;
  }
  return (
    <View style={styles.voice}>
      <Button
        icon={recognition.listening ? MicOff : Mic}
        label={
          recognition.listening ? "Zakończ dyktowanie" : "Powiedz zamiast pisać"
        }
        onPress={recognition.listening ? recognition.stop : recognition.start}
        pressed={recognition.listening}
      />
      <View aria-live="polite">
        {recognition.listening ? (
          <Txt tone="stamp" weight="500">
            Słucham. Mów po polsku, a tekst pojawi się w polu.
          </Txt>
        ) : null}
        {recognition.error ? (
          <Txt tone="bad" weight="500">
            {recognition.error}
          </Txt>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  voice: {
    gap: space.sm,
  },
});
