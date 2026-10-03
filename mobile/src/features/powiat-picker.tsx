import { Check, ChevronDown, ChevronUp, MapPin, X } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import Svg, { Path } from "react-native-svg";
import { useMap } from "@/hooks/use-map";
import type { SelectOption } from "@/lib/options";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

const EVERYWHERE = "Cała Małopolska";

interface PowiatPickerProps {
  night?: boolean;
  onChange: (slug: string) => void;
  options: SelectOption[];
  required?: boolean;
  value: string;
}

const usePalette = (night: boolean) => {
  const { colors } = useTheme();
  return night
    ? {
        chosen: colors.onNight,
        chosenEdge: colors.night,
        edge: colors.onNightSoft,
        ink: colors.onNight,
        land: colors.nightRise,
        soft: colors.onNightSoft,
      }
    : {
        chosen: colors.stamp,
        chosenEdge: colors.paper,
        edge: colors.ruleStrong,
        ink: colors.ink,
        land: colors.tone,
        soft: colors.inkSoft,
      };
};

function RegionMap({
  night = true,
  onChange,
  value,
}: Omit<PowiatPickerProps, "options">) {
  const { highContrast } = useTheme();
  const palette = usePalette(night);
  const { projection } = useMap();
  if (!projection) {
    return null;
  }
  return (
    <View
      aria-hidden
      style={{ aspectRatio: projection.width / projection.height }}
    >
      <Svg
        height="100%"
        viewBox={`0 0 ${projection.width} ${projection.height}`}
        width="100%"
      >
        {projection.shapes.map((shape) => {
          const active = shape.slug === value;
          return (
            <Path
              d={shape.d}
              fill={active ? palette.chosen : palette.land}
              key={shape.slug}
              onPress={() => onChange(active ? "" : shape.slug)}
              stroke={active ? palette.chosenEdge : palette.edge}
              strokeLinejoin="round"
              strokeWidth={highContrast ? 4 : 2.5}
            />
          );
        })}
      </Svg>
    </View>
  );
}

function NameList({
  night = true,
  onChange,
  options,
  value,
}: PowiatPickerProps) {
  const palette = usePalette(night);
  return (
    <View aria-label="Powiaty" role="group" style={styles.names}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <Pressable
            aria-pressed={active}
            key={option.value}
            onPress={() => onChange(active ? "" : option.value)}
            role="button"
            style={styles.name}
          >
            {active ? (
              <Check aria-hidden color={palette.ink} size={20} />
            ) : null}
            <Txt
              style={[
                styles.grow,
                { color: active ? palette.ink : palette.soft },
              ]}
              variant="label"
              weight={active ? "600" : "400"}
            >
              {option.label}
            </Txt>
          </Pressable>
        );
      })}
    </View>
  );
}

export function PowiatPicker({
  night = true,
  onChange,
  options,
  required = false,
  value,
}: PowiatPickerProps) {
  const { wide } = useTheme();
  const palette = usePalette(night);
  const nothing = required ? "Wybierz powiat" : EVERYWHERE;
  const [open, setOpen] = useState(false);
  const name = options.find((option) => option.value === value)?.label;
  const Chevron = open ? ChevronUp : ChevronDown;
  const pick = (slug: string) => {
    onChange(slug);
    if (!wide && slug) {
      setOpen(false);
    }
  };
  const showMap = wide || open;
  return (
    <View style={styles.wrap}>
      <View style={styles.head}>
        <Txt style={{ color: palette.soft }} variant="label">
          {wide
            ? "Gdzie to jest? Powiat można wskazać na mapie."
            : "Gdzie to jest? Powiat można wybrać z listy."}
        </Txt>
      </View>
      {showMap ? (
        <RegionMap night={night} onChange={pick} value={value} />
      ) : null}
      <View style={styles.bar}>
        <Pressable
          aria-expanded={open}
          aria-label={`Powiat${required ? "" : ", nieobowiązkowo"}: ${name ?? nothing}. ${open ? "Zwiń listę" : "Wybierz z listy"}`}
          onPress={() => setOpen((current) => !current)}
          role="button"
          style={styles.trigger}
        >
          <MapPin aria-hidden color={palette.ink} size={24} />
          <Txt
            style={[styles.grow, { color: palette.ink }]}
            variant="label"
            weight="600"
          >
            {name ?? nothing}
          </Txt>
          <Chevron aria-hidden color={palette.soft} size={22} />
        </Pressable>
        {value ? (
          <Pressable
            aria-label="Usuń wybór powiatu"
            onPress={() => onChange("")}
            role="button"
            style={styles.clear}
          >
            <X aria-hidden color={palette.soft} size={22} />
          </Pressable>
        ) : null}
      </View>
      {open ? (
        <NameList
          night={night}
          onChange={pick}
          options={options}
          value={value}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.xs,
  },
  clear: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: minTarget,
    justifyContent: "center",
    width: minTarget,
  },
  grow: {
    flexShrink: 1,
  },
  head: {
    marginBottom: space.xs,
  },
  name: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
    width: "50%",
  },
  names: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  trigger: {
    alignItems: "center",
    borderRadius: radius.md,
    flexDirection: "row",
    flexShrink: 1,
    gap: space.sm + 2,
    minHeight: minTarget + 4,
  },
  wrap: {
    gap: space.sm,
  },
});
