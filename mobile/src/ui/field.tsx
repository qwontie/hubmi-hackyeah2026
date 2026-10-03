import { Check } from "lucide-react-native";
import { type Ref, useId, useState } from "react";
import {
  Pressable,
  StyleSheet,
  TextInput,
  type TextInputProps,
  View,
} from "react-native";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Txt } from "./text";

const fieldBorder = (
  focused: boolean,
  invalid: boolean,
  colors: { ring: string; bad: string; ruleStrong: string }
) => {
  if (focused) {
    return colors.ring;
  }
  return invalid ? colors.bad : colors.ruleStrong;
};

interface FieldProps extends Omit<TextInputProps, "style"> {
  error?: string | null;
  hideLabel?: boolean;
  hint?: string;
  label: string;
  labelledBy?: string;
  large?: boolean;
  rows?: number;
}

export const TextField = function TextField({
  label,
  hint,
  error,
  labelledBy,
  hideLabel = false,
  large = false,
  multiline,
  rows = 5,
  ref,
  ...rest
}: FieldProps & { ref?: Ref<TextInput> }) {
  const { colors, type, lineHeight, borderWidth } = useTheme();
  const [focused, setFocused] = useState(false);
  const id = useId();
  const labelId = `${id}-label`;
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null]
    .filter(Boolean)
    .join(" ");
  const fontSize = large ? type.lead : type.body;
  return (
    <View style={styles.wrap}>
      {labelledBy || hideLabel ? null : (
        <Txt nativeID={labelId} variant="label" weight="600">
          {label}
        </Txt>
      )}
      {hint ? (
        <Txt nativeID={hintId} tone="soft" variant="small">
          {hint}
        </Txt>
      ) : null}
      <TextInput
        accessibilityLabel={label}
        aria-describedby={describedBy || undefined}
        aria-invalid={error ? true : undefined}
        aria-labelledby={hideLabel ? undefined : (labelledBy ?? labelId)}
        multiline={multiline}
        onBlur={(event) => {
          setFocused(false);
          rest.onBlur?.(event);
        }}
        onFocus={(event) => {
          setFocused(true);
          rest.onFocus?.(event);
        }}
        placeholderTextColor={colors.inkSoft}
        ref={ref}
        style={[
          styles.input,
          {
            backgroundColor: colors.sunk,
            borderColor: fieldBorder(focused, Boolean(error), colors),
            borderWidth: error || focused ? 2 : Math.max(borderWidth, 1.5),
            color: colors.ink,
            fontSize,
            lineHeight: lineHeight(fontSize),
            minHeight: multiline
              ? lineHeight(fontSize) * rows + 32
              : minTarget + 8,
            textAlignVertical: multiline ? "top" : "center",
          },
        ]}
        {...rest}
      />
      {error ? (
        <Txt nativeID={errorId} tone="bad" variant="body" weight="500">
          {error}
        </Txt>
      ) : null}
    </View>
  );
};

interface CheckboxProps {
  checked: boolean;
  error?: string | null;
  label: string;
  onChange: (checked: boolean) => void;
}

export function Checkbox({ checked, onChange, label, error }: CheckboxProps) {
  const { colors, borderWidth } = useTheme();
  return (
    <View style={styles.wrap}>
      <Pressable
        aria-checked={checked}
        aria-invalid={error ? true : undefined}
        onPress={() => onChange(!checked)}
        role="checkbox"
        style={styles.checkRow}
      >
        <View
          style={[
            styles.box,
            {
              backgroundColor: checked ? colors.stamp : colors.paper,
              borderColor: error ? colors.bad : colors.ruleStrong,
              borderWidth: Math.max(2, borderWidth),
            },
          ]}
        >
          {checked ? (
            <Check
              aria-hidden
              color={colors.onStamp}
              size={20}
              strokeWidth={3}
            />
          ) : null}
        </View>
        <Txt style={styles.checkLabel}>{label}</Txt>
      </Pressable>
      {error ? (
        <Txt tone="bad" weight="500">
          {error}
        </Txt>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    alignItems: "center",
    borderRadius: 10,
    height: 30,
    justifyContent: "center",
    marginTop: 1,
    width: 30,
  },
  checkLabel: {
    flex: 1,
  },
  checkRow: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget,
    paddingVertical: space.xs,
  },
  input: {
    borderRadius: radius.button,
    paddingHorizontal: space.lg + 4,
    paddingVertical: space.lg,
  },
  wrap: {
    gap: space.sm,
  },
});
