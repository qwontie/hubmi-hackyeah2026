import { type Href, Link, router } from "expo-router";
import { ArrowRight, MessageSquareText } from "lucide-react-native";
import { useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
  type ViewStyle,
} from "react-native";
import { formatDate } from "@/lib/plural";
import type { StoredIdea } from "@/storage/ideas";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { Button } from "@/ui/button";
import { nightAttr } from "@/ui/night";
import { Sheet } from "@/ui/sheet";
import { Heading, Txt } from "@/ui/text";

export const HUB_WIDTH = 1180;
const LONGEST_WORD = 11;
const GLYPH = 0.6;
const ARROW = 60;

const ease = (property: string): ViewStyle =>
  (Platform.OS === "web"
    ? {
        transitionDuration: "320ms",
        transitionProperty: property,
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
      }
    : {}) as ViewStyle;

export type DoorTone = "night" | "dusk" | "day";

interface DoorProps {
  href: Href;
  text: string;
  title: string;
  tone: DoorTone;
}

const useDoorInk = (tone: DoorTone) => {
  const { colors } = useTheme();
  return {
    day: {
      arrow: colors.stamp,
      arrowInk: colors.onStamp,
      ground: colors.tone,
      ink: colors.ink,
      soft: colors.inkSoft,
    },
    dusk: {
      arrow: colors.onStamp,
      arrowInk: colors.stamp,
      ground: colors.stamp,
      ink: colors.onStamp,
      soft: colors.onStamp,
    },
    night: {
      arrow: colors.onNight,
      arrowInk: colors.night,
      ground: colors.night,
      ink: colors.onNight,
      soft: colors.onNightSoft,
    },
  }[tone];
};

const useTitleSize = () => {
  const { type, wide } = useTheme();
  const { width } = useWindowDimensions();
  const column = wide
    ? (Math.min(width - 2 * space.xxl, HUB_WIDTH) - 2 * space.lg) / 3 -
      2 * space.xxl
    : width - 2 * space.lg - 2 * space.xl - ARROW - space.lg;
  const fit = Math.floor(column / (LONGEST_WORD * GLYPH));
  return Math.min(wide ? type.h1 : type.h2, fit);
};

export function Door({ href, text, title, tone }: DoorProps) {
  const { colors, highContrast, reduceMotion, wide } = useTheme();
  const [hot, setHot] = useState(false);
  const ink = useDoorInk(tone);
  const size = useTitleSize();
  const lively = hot && !reduceMotion;
  return (
    <Link asChild href={href}>
      <Pressable
        aria-label={`${title}. ${text}`}
        onBlur={() => setHot(false)}
        onFocus={() => setHot(true)}
        onHoverIn={() => setHot(true)}
        onHoverOut={() => setHot(false)}
        role="link"
        style={StyleSheet.flatten([
          styles.door,
          wide ? styles.doorWide : styles.doorNarrow,
          ease("flex-grow"),
          {
            backgroundColor: ink.ground,
            borderColor: highContrast ? colors.ink : "transparent",
            borderWidth: highContrast ? 2 : 0,
            flexGrow: wide && lively ? 1.16 : 1,
          },
        ])}
        {...nightAttr(tone !== "day")}
      >
        <View style={styles.words}>
          <Txt
            style={{
              color: ink.ink,
              fontSize: size,
              letterSpacing: size * -0.032,
              lineHeight: Math.round(size * 1.08),
            }}
            weight="600"
          >
            {title}
          </Txt>
          <Txt style={{ color: ink.soft }} variant={wide ? "lead" : "body"}>
            {text}
          </Txt>
        </View>
        <View
          style={[
            styles.arrow,
            ease("transform"),
            {
              backgroundColor: ink.arrow,
              transform: [{ translateX: lively ? 8 : 0 }],
            },
          ]}
        >
          <ArrowRight
            aria-hidden
            color={ink.arrowInk}
            size={28}
            strokeWidth={2.2}
          />
        </View>
      </Pressable>
    </Link>
  );
}

export function DoorRow({
  href,
  text,
  title,
}: {
  href: Href;
  text: string;
  title: string;
}) {
  const { colors, highContrast } = useTheme();
  const [hot, setHot] = useState(false);
  return (
    <Link asChild href={href}>
      <Pressable
        onHoverIn={() => setHot(true)}
        onHoverOut={() => setHot(false)}
        role="link"
        style={StyleSheet.flatten([
          styles.doorRow,
          {
            backgroundColor: hot ? colors.tone : colors.paper,
            borderColor: highContrast ? colors.ink : colors.tone,
            borderWidth: highContrast ? 2 : 1,
          },
        ])}
      >
        <View style={styles.words}>
          <Txt variant="lead" weight="600">
            {title}
          </Txt>
          <Txt tone="soft">{text}</Txt>
        </View>
        <View style={styles.fixed}>
          <ArrowRight aria-hidden color={colors.stamp} size={26} />
        </View>
      </Pressable>
    </Link>
  );
}

export function Doors({ doors }: { doors: DoorProps[] }) {
  const { wide } = useTheme();
  return (
    <View
      aria-label="Sposoby działania"
      role="navigation"
      style={[styles.doors, wide && styles.doorsWide]}
    >
      {doors.map((door) => (
        <Door key={door.title} {...door} />
      ))}
    </View>
  );
}

export function MyIdeas({ ideas }: { ideas: StoredIdea[] }) {
  const { colors, wide } = useTheme();
  if (ideas.length === 0) {
    return null;
  }
  return (
    <Sheet>
      <View style={styles.listHead}>
        <Heading level={2}>Moje pomysły</Heading>
        <Txt tone="soft">Zapisane na tym urządzeniu.</Txt>
      </View>
      <View role="list">
        {ideas.map((idea, index) => (
          <View
            key={idea.id}
            role="listitem"
            style={[
              styles.row,
              wide && styles.rowWide,
              { borderTopColor: colors.rule },
              index === 0 && styles.first,
            ]}
          >
            <View style={styles.rowText}>
              <Txt variant="lead" weight="600">
                {idea.title}
              </Txt>
              <Txt tone="soft" variant="detail">
                {[
                  idea.number ? `Pomysł nr ${idea.number}` : null,
                  `wysłany ${formatDate(idea.createdAt)}`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </Txt>
            </View>
            <Button
              fill={!wide}
              icon={MessageSquareText}
              label="Rozmowa z ROPS"
              onPress={() =>
                router.push({
                  params: { id: idea.id },
                  pathname: "/pomysl/[id]",
                })
              }
            />
          </View>
        ))}
      </View>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  arrow: {
    alignItems: "center",
    borderRadius: radius.pill,
    height: ARROW,
    justifyContent: "center",
    width: ARROW,
  },
  door: {
    borderRadius: radius.sheet,
    flexBasis: 0,
    flexShrink: 1,
    gap: space.lg,
    overflow: "hidden",
    ...Platform.select({ default: {}, web: { cursor: "pointer" } }),
  },
  doorNarrow: {
    alignItems: "center",
    flexBasis: "auto",
    flexDirection: "row",
    flexShrink: 0,
    padding: space.xl,
  },
  doorRow: {
    alignItems: "center",
    borderRadius: radius.sheet,
    flexDirection: "row",
    gap: space.lg,
    justifyContent: "space-between",
    paddingHorizontal: space.xl,
    paddingVertical: space.lg + 2,
    ...Platform.select({ default: {}, web: { cursor: "pointer" } }),
  },
  doors: {
    gap: space.md,
  },
  doorsWide: {
    flexDirection: "row",
    gap: space.lg,
  },
  doorWide: {
    justifyContent: "space-between",
    minHeight: 340,
    padding: space.xxl,
  },
  first: {
    borderTopWidth: 0,
  },
  fixed: {
    flexShrink: 0,
  },
  listHead: {
    gap: space.xs,
  },
  row: {
    borderTopWidth: 1,
    gap: space.md,
    paddingVertical: space.lg,
  },
  rowText: {
    flex: 1,
    gap: space.xs,
  },
  rowWide: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.xl,
  },
  words: {
    flexShrink: 1,
    gap: space.sm,
  },
});
