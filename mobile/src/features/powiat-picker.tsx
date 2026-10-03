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
  onChange: (slug: string) => void;
  options: SelectOption[];
  value: string;
}

function RegionMap({ onChange, value }: Omit<PowiatPickerProps, "options">) {
  const { colors, highContrast } = useTheme();
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
              fill={active ? colors.onNight : colors.nightRise}
              key={shape.slug}
              onPress={() => onChange(active ? "" : shape.slug)}
              stroke={highContrast ? colors.onNight : colors.night}
              strokeLinejoin="round"
              strokeWidth={highContrast ? 3 : 5}
            />
          );
        })}
      </Svg>
    </View>
  );
}

function NameList({ onChange, options, value }: PowiatPickerProps) {
  const { colors } = useTheme();
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
              <Check aria-hidden color={colors.onNight} size={20} />
            ) : null}
            <Txt
              style={styles.grow}
              tone={active ? "onNight" : "onNightSoft"}
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

export function PowiatPicker({ onChange, options, value }: PowiatPickerProps) {
  const { colors, wide } = useTheme();
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
      {wide ? (
        <View style={styles.head}>
          <Txt tone="onNightSoft" variant="label">
            Gdzie to jest? Powiat można wskazać na mapie.
          </Txt>
        </View>
      ) : null}
      {showMap ? <RegionMap onChange={pick} value={value} /> : null}
      <View style={styles.bar}>
        <Pressable
          aria-expanded={open}
          aria-label={`Powiat, nieobowiązkowo: ${name ?? EVERYWHERE}. ${open ? "Zwiń listę" : "Wybierz z listy"}`}
          onPress={() => setOpen((current) => !current)}
          role="button"
          style={styles.trigger}
        >
          <MapPin aria-hidden color={colors.onNight} size={24} />
          <Txt style={styles.grow} tone="onNight" variant="label" weight="600">
            {name ?? EVERYWHERE}
          </Txt>
          <Chevron aria-hidden color={colors.onNightSoft} size={22} />
        </Pressable>
        {value ? (
          <Pressable
            aria-label="Usuń wybór powiatu"
            onPress={() => onChange("")}
            role="button"
            style={styles.clear}
          >
            <X aria-hidden color={colors.onNightSoft} size={22} />
          </Pressable>
        ) : null}
      </View>
      {open ? (
        <NameList onChange={pick} options={options} value={value} />
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
