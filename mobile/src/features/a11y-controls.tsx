import {
  ALargeSmall,
  Check,
  CirclePause,
  Contrast,
  type LucideIcon,
  Square,
  Volume2,
  X,
} from "lucide-react-native";
import { useRef, useState } from "react";
import { Modal, Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useA11yControls } from "@/hooks/use-a11y-controls";
import { focusElement } from "@/lib/a11y";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Glass } from "@/ui/glass";
import { nightAttr } from "@/ui/night";
import { Heading, Txt } from "@/ui/text";

const WASH = "rgba(252, 252, 255, 0.14)";
const SIZE_WORDS: Record<string, string> = {
  large: "duży",
  standard: "standardowy",
  xlarge: "bardzo duży",
};

interface TileProps {
  hint: string;
  icon: LucideIcon;
  label: string;
  night: boolean;
  on?: boolean;
  onPress: () => void;
  state?: string;
}

function Tile({ hint, icon, label, night, on, onPress, state }: TileProps) {
  const { colors, highContrast, reduceMotion, wide } = useTheme();
  const [hovered, setHovered] = useState(false);
  const active = on === true;
  const Icon = active ? Check : icon;
  const rest = night ? WASH : colors.tone;
  const hover = night ? "rgba(252, 252, 255, 0.22)" : colors.toneHover;
  const fill = night ? colors.onNight : colors.stamp;
  const restInk = night ? colors.onNight : colors.stamp;
  const activeInk = night ? colors.night : colors.onStamp;
  const ink = active ? activeInk : restInk;
  const idle = hovered ? hover : rest;
  return (
    <Pressable
      aria-label={hint}
      aria-pressed={on}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={onPress}
      role="button"
      style={({ pressed }) => [
        styles.tile,
        wide ? styles.tileWide : styles.tileNarrow,
        {
          backgroundColor: active ? fill : idle,
          borderColor: highContrast ? ink : "transparent",
          borderWidth: highContrast ? 2 : 0,
          transform: [{ scale: pressed && !reduceMotion ? 0.96 : 1 }],
        },
      ]}
    >
      <Icon aria-hidden color={ink} size={26} strokeWidth={2.2} />
      <View style={wide ? styles.wordsWide : styles.words}>
        <Txt
          maxFontSizeMultiplier={1.3}
          style={[styles.tileLabel, wide && styles.centered, { color: ink }]}
          weight="600"
        >
          {label}
        </Txt>
        {state ? (
          <Txt
            maxFontSizeMultiplier={1.3}
            style={[styles.tileState, wide && styles.centered, { color: ink }]}
          >
            {state}
          </Txt>
        ) : null}
      </View>
    </Pressable>
  );
}

export function A11yControls({ night = false }: { night?: boolean }) {
  const { contrast, motion, read, text } = useA11yControls();
  const size = SIZE_WORDS[text.value] ?? "";
  return (
    <View aria-label="Dostępność" role="group" style={styles.row}>
      <Tile
        hint={`Tekst: ${size}. Zmień wielkość tekstu`}
        icon={ALargeSmall}
        label="Tekst"
        night={night}
        onPress={text.cycle}
        state={size}
      />
      <Tile
        hint={contrast.on ? "Kontrast: wysoki, włączony" : "Kontrast wysoki"}
        icon={Contrast}
        label="Kontrast"
        night={night}
        on={contrast.on}
        onPress={contrast.toggle}
      />
      <Tile
        hint={motion.on ? "Mniej ruchu: włączone" : "Mniej ruchu"}
        icon={CirclePause}
        label="Mniej ruchu"
        night={night}
        on={motion.on}
        onPress={motion.toggle}
      />
      {read.supported ? (
        <Tile
          hint={read.on ? "Zatrzymaj czytanie" : "Posłuchaj strony"}
          icon={read.on ? Square : Volume2}
          label={read.on ? "Zatrzymaj" : "Posłuchaj"}
          night={night}
          onPress={() => read.toggle()}
        />
      ) : null}
    </View>
  );
}

export function A11yPanel({
  onClose,
  open,
}: {
  onClose: () => void;
  open: boolean;
}) {
  const { colors, highContrast, reduceMotion, wide } = useTheme();
  const insets = useSafeAreaInsets();
  const close = useRef<View>(null);
  return (
    <Modal
      accessibilityLabel="Dostępność"
      animationType={reduceMotion ? "none" : "fade"}
      aria-label="Dostępność"
      onRequestClose={onClose}
      onShow={() => focusElement(close.current)}
      transparent
      visible={open}
    >
      <View
        aria-hidden
        onResponderRelease={onClose}
        onStartShouldSetResponder={() => true}
        style={styles.backdrop}
      />
      <View
        pointerEvents="box-none"
        style={[
          styles.dock,
          wide
            ? styles.dockWide
            : { paddingTop: insets.top + minTarget + space.lg },
        ]}
      >
        <View
          aria-label="Dostępność"
          role="group"
          style={[
            styles.panel,
            {
              backgroundColor: colors.paper,
              borderColor: highContrast ? colors.ink : colors.tone,
              borderWidth: highContrast ? 2 : 1,
            },
          ]}
          {...nightAttr(false)}
        >
          <View style={styles.panelHead}>
            <Heading level={2} size="h3">
              Dostępność
            </Heading>
            <Pressable
              aria-label="Zamknij"
              onPress={onClose}
              ref={close}
              role="button"
              style={styles.close}
            >
              <X aria-hidden color={colors.ink} size={24} />
            </Pressable>
          </View>
          <A11yControls />
        </View>
      </View>
    </Modal>
  );
}

export function A11yButton({
  labelled = false,
  night = false,
}: {
  labelled?: boolean;
  night?: boolean;
}) {
  const { colors, wide } = useTheme();
  const [open, setOpen] = useState(false);
  if (wide) {
    return null;
  }
  const ink = night ? colors.onNight : colors.ink;
  return (
    <>
      <Pressable
        aria-expanded={open}
        aria-label="Dostępność: wielkość tekstu, kontrast, czytanie"
        onPress={() => setOpen(true)}
        role="button"
        style={styles.round}
      >
        <Glass
          interactive
          night={night}
          style={labelled ? styles.pillGlass : styles.roundGlass}
        >
          <ALargeSmall aria-hidden color={ink} size={26} strokeWidth={2} />
          {labelled ? (
            <Txt
              maxFontSizeMultiplier={1.3}
              style={{ color: ink }}
              variant="label"
              weight="600"
            >
              Dostępność
            </Txt>
          ) : null}
        </Glass>
      </Pressable>
      <A11yPanel onClose={() => setOpen(false)} open={open} />
    </>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: "rgba(17, 9, 56, 0.28)",
    bottom: 0,
    left: 0,
    position: "absolute",
    right: 0,
    top: 0,
  },
  centered: {
    textAlign: "center",
  },
  close: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: minTarget,
    justifyContent: "center",
    width: minTarget,
  },
  dock: {
    alignItems: "flex-end",
    flex: 1,
    paddingHorizontal: space.lg,
  },
  dockWide: {
    paddingHorizontal: 40,
    paddingTop: 92,
  },
  panel: {
    borderRadius: radius.sheet,
    gap: space.md,
    maxWidth: 460,
    padding: space.lg + 2,
    width: "100%",
  },
  panelHead: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  pillGlass: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget + 4,
    paddingHorizontal: space.lg,
  },
  round: {
    borderRadius: radius.pill,
  },
  roundGlass: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: minTarget + 4,
    justifyContent: "center",
    width: minTarget + 4,
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
  },
  tile: {
    alignItems: "center",
    borderRadius: 18,
    justifyContent: "center",
    paddingVertical: space.sm,
  },
  tileLabel: {
    fontSize: 15,
    lineHeight: 19,
  },
  tileNarrow: {
    flexBasis: "47%",
    flexDirection: "row",
    flexGrow: 1,
    gap: space.sm + 2,
    justifyContent: "flex-start",
    minHeight: 56,
    paddingHorizontal: space.md + 2,
  },
  tileState: {
    fontSize: 13,
    lineHeight: 16,
  },
  tileWide: {
    flex: 1,
    gap: 2,
    minHeight: 84,
    paddingHorizontal: space.xs,
  },
  words: {
    flexShrink: 1,
  },
  wordsWide: {
    alignItems: "center",
  },
});
