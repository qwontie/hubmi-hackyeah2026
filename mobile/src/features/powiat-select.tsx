import { Check, ChevronDown } from "lucide-react-native";
import { useState } from "react";
import { Modal, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import type { Powiat } from "@/api/types";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { Heading, Txt } from "@/ui/text";

interface PowiatSelectProps {
  onChange: (value: string) => void;
  powiats: Powiat[];
  value: string;
}

export function PowiatSelect({ powiats, value, onChange }: PowiatSelectProps) {
  const { colors, borderWidth } = useTheme();
  const [open, setOpen] = useState(false);
  const selected = powiats.find((powiat) => powiat.slug === value);
  const options = [{ name: "Nie wybieram", slug: "" }, ...powiats];
  return (
    <View style={styles.wrap}>
      <Txt variant="label" weight="600">
        Powiat <Txt tone="soft">(nieobowiązkowo)</Txt>
      </Txt>
      <Pressable
        accessibilityHint="Otwiera listę powiatów"
        accessibilityLabel={`Powiat: ${selected?.name ?? "nie wybrano"}`}
        onPress={() => setOpen(true)}
        role="button"
        style={[
          styles.trigger,
          {
            backgroundColor: colors.sunk,
            borderColor: colors.ruleStrong,
            borderWidth,
          },
        ]}
      >
        <Txt>{selected?.name ?? "Nie wybieram"}</Txt>
        <ChevronDown aria-hidden color={colors.inkSoft} size={22} />
      </Pressable>
      <Modal
        animationType="slide"
        onRequestClose={() => setOpen(false)}
        presentationStyle="pageSheet"
        visible={open}
      >
        <SafeAreaView style={[styles.modal, { backgroundColor: colors.paper }]}>
          <View style={styles.modalHead}>
            <Heading level={2}>Wybierz powiat</Heading>
            <Button
              label="Zamknij"
              onPress={() => setOpen(false)}
              variant="quiet"
            />
          </View>
          <ScrollView contentContainerStyle={styles.list}>
            {options.map((option) => {
              const active = option.slug === value;
              return (
                <Pressable
                  aria-selected={active}
                  key={option.slug || "none"}
                  onPress={() => {
                    onChange(option.slug);
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
                  <Txt weight={active ? "600" : "400"}>{option.name}</Txt>
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
