import { useId } from "react";
import { StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";
import { fonts, minTarget, radius, space } from "@/theme/tokens";
import type { SelectProps } from "./select";
import { Txt } from "./text";

export function Select({
  label,
  optional = false,
  options,
  value,
  onChange,
  emptyLabel,
  error,
}: SelectProps) {
  const { colors, type, borderWidth } = useTheme();
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <View style={styles.wrap}>
      <label htmlFor={id}>
        <Txt variant="label" weight="600">
          {label}
          {optional ? <Txt tone="soft"> (nieobowiązkowo)</Txt> : null}
        </Txt>
      </label>
      <select
        aria-describedby={error ? errorId : undefined}
        aria-invalid={error ? true : undefined}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        style={{
          appearance: "auto",
          background: colors.sunk,
          border: `${error ? 2 : borderWidth}px solid ${error ? colors.bad : colors.ruleStrong}`,
          borderRadius: radius.md,
          color: colors.ink,
          fontFamily: fonts["400"],
          fontSize: type.body,
          maxWidth: 480,
          minHeight: minTarget + 8,
          padding: `0 ${space.md}px`,
          width: "100%",
        }}
        value={value}
      >
        {emptyLabel ? <option value="">{emptyLabel}</option> : null}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error ? (
        <Txt nativeID={errorId} tone="bad" weight="500">
          {error}
        </Txt>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: space.sm,
  },
});
