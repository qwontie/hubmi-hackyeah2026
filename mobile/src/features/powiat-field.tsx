import { StyleSheet, View } from "react-native";
import { PowiatPicker } from "@/features/powiat-picker";
import { usePowiats } from "@/hooks/use-powiats";
import { space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

export function PowiatField({
  error,
  onChange,
  value,
}: {
  error: string | null;
  onChange: (slug: string) => void;
  value: string;
}) {
  const powiats = usePowiats();
  return (
    <View style={styles.block}>
      <PowiatPicker
        mapWidth={340}
        night={false}
        onChange={onChange}
        options={powiats.options}
        required
        value={value}
      />
      {error ? (
        <Txt tone="bad" weight="500">
          {error}
        </Txt>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    gap: space.md,
  },
});
