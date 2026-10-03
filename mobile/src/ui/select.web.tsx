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
  night = false,
  compact = false,
}: SelectProps) {
  const { colors, type, borderWidth } = useTheme();
  const ink = night ? colors.onNight : colors.ink;
  const soft = night ? colors.onNightSoft : colors.inkSoft;
  const edge = night ? soft : colors.ruleStrong;
  const id = useId();
  const errorId = `${id}-error`;
  if (compact) {
    return (
      <select
        aria-label={optional ? `${label} (nieobowiązkowo)` : label}
        onChange={(event) => onChange(event.target.value)}
        style={{
          appearance: "auto",
          background: night ? "transparent" : colors.sunk,
          border: `1px solid ${edge}`,
          borderRadius: radius.pill,
          color: ink,
          fontFamily: fonts["500"],
          fontSize: type.label,
          height: minTarget + 4,
          maxWidth: 210,
          minWidth: 0,
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
    );
  }
  return (
    <View style={styles.wrap}>
      <label htmlFor={id}>
        <Txt style={{ color: ink }} variant="label" weight="600">
          {label}
          {optional ? (
            <Txt style={{ color: soft }}> (nieobowiązkowo)</Txt>
          ) : null}
        </Txt>
      </label>
      <select
        aria-describedby={error ? errorId : undefined}
        aria-invalid={error ? true : undefined}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        style={{
          appearance: "auto",
          background: night ? colors.nightDeep : colors.sunk,
          border: `${error ? 2 : Math.max(borderWidth, 1.5)}px solid ${error ? colors.bad : edge}`,
          borderRadius: radius.button,
          color: ink,
          fontFamily: fonts["400"],
          fontSize: type.body,
          maxWidth: 480,
          minHeight: minTarget + 8,
          padding: `0 ${space.lg}px`,
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
