import { Check, ChevronDown } from "lucide-react-native";
import { useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "./button";
import { Heading, Txt } from "./text";

export interface SelectOption {
  label: string;
  value: string;
}

export interface SelectProps {
  emptyLabel?: string;
  error?: string | null;
  label: string;
  onChange: (value: string) => void;
  optional?: boolean;
  options: SelectOption[];
  value: string;
}

export function Select({
  label,
  optional = false,
  options,
  value,
  onChange,
  emptyLabel,
  error,
}: SelectProps) {
  const { colors, borderWidth } = useTheme();
  const [open, setOpen] = useState(false);
  const all = emptyLabel
    ? [{ label: emptyLabel, value: "" }, ...options]
    : options;
  const selected = all.find((option) => option.value === value);
  return (
    <View style={styles.wrap}>
      <Txt variant="label" weight="600">
        {label}
        {optional ? <Txt tone="soft"> (nieobowiązkowo)</Txt> : null}
      </Txt>
      <Pressable
        accessibilityHint="Otwiera listę do wyboru"
        accessibilityLabel={`${label}: ${selected?.label ?? "nie wybrano"}`}
        onPress={() => setOpen(true)}
        role="button"
        style={[
          styles.trigger,
          {
            backgroundColor: colors.sunk,
            borderColor: error ? colors.bad : colors.ruleStrong,
            borderWidth: error ? 2 : borderWidth,
          },
        ]}
      >
        <Txt>{selected?.label ?? "Wybierz"}</Txt>
        <ChevronDown aria-hidden color={colors.inkSoft} size={22} />
      </Pressable>
      {error ? (
        <Txt tone="bad" weight="500">
          {error}
        </Txt>
      ) : null}
      <Modal
        animationType="slide"
        onRequestClose={() => setOpen(false)}
        presentationStyle="pageSheet"
        visible={open}
      >
        <SafeAreaView style={[styles.modal, { backgroundColor: colors.paper }]}>
          <View style={styles.modalHead}>
            <Heading level={2}>{label}</Heading>
            <Button
              label="Zamknij"
              onPress={() => setOpen(false)}
              variant="quiet"
            />
          </View>
          <ScrollView contentContainerStyle={styles.list}>
            {all.map((option) => {
              const active = option.value === value;
              return (
                <Pressable
                  aria-selected={active}
                  key={option.value || "none"}
                  onPress={() => {
                    onChange(option.value);
                    setOpen(false);
                  }}
                  role="button"
                  style={[
                    styles.option,
                    {
                      backgroundColor: active
                        ? colors.stampWash
                        : "transparent",
                      borderBottomColor: colors.rule,
                    },
                  ]}
                >
                  <Txt weight={active ? "600" : "400"}>{option.label}</Txt>
                  {active ? (
                    <Check aria-hidden color={colors.stamp} size={22} />
                  ) : null}
                </Pressable>
              );
            })}
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  list: {
    paddingBottom: space.xxxl,
  },
  modal: {
    flex: 1,
  },
  modalHead: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    padding: space.lg,
  },
  option: {
    alignItems: "center",
    borderBottomWidth: StyleSheet.hairlineWidth,
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: minTarget + 8,
    paddingHorizontal: space.lg,
  },
  trigger: {
    alignItems: "center",
    borderRadius: radius.md,
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: minTarget + 8,
    paddingHorizontal: space.lg,
  },
  wrap: {
    gap: space.sm,
  },
});
