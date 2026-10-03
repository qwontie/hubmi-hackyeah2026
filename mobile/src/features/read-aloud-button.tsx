import { Square, Volume2 } from "lucide-react-native";
import { useReadAloud } from "@/speech/read-aloud";
import { Button } from "@/ui/button";

export function ReadAloudButton({ text }: { text: string }) {
  const { supported, speaking, toggle } = useReadAloud();
  if (!supported) {
    return null;
  }
  return (
    <Button
      icon={speaking ? Square : Volume2}
      label={speaking ? "Zatrzymaj czytanie" : "Przeczytaj na głos"}
      onPress={() => toggle(text)}
      pressed={speaking}
    />
  );
}
