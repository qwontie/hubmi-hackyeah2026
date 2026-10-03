import { useId } from "react";
import { StyleSheet, View } from "react-native";
import type { Powiat } from "@/api/types";
import { useTheme } from "@/theme/settings";
import { fonts, minTarget, radius, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

interface PowiatSelectProps {
  onChange: (value: string) => void;
  powiats: Powiat[];
  value: string;
}

export function PowiatSelect({ powiats, value, onChange }: PowiatSelectProps) {
  const { colors, type, borderWidth } = useTheme();
  const id = useId();
  return (
    <View style={styles.wrap}>
      <label htmlFor={id}>
        <Txt variant="label" weight="600">
          Powiat <Txt tone="soft">(nieobowiązkowo)</Txt>
        </Txt>
      </label>
      <select
        id={id}
        onChange={(event) => onChange(event.target.value)}
        style={{
          appearance: "auto",
          background: colors.sunk,
          border: `${borderWidth}px solid ${colors.ruleStrong}`,
          borderRadius: radius.md,
          color: colors.ink,
          fontFamily: fonts["400"],
          fontSize: type.body,
          maxWidth: 420,
          minHeight: minTarget + 8,
          padding: `0 ${space.md}px`,
          width: "100%",
        }}
        value={value}
      >
        <option value="">Nie wybieram</option>
        {powiats.map((powiat) => (
          <option key={powiat.slug} value={powiat.slug}>
            {powiat.name}
          </option>
        ))}
      </select>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: space.sm,
  },
});
