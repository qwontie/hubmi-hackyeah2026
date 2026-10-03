import { Image } from "expo-image";
import { Link } from "expo-router";
import {
  ArrowRight,
  type LucideIcon,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react-native";
import { type ReactNode, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";
import type { FeedbackKind, InnovationSummary } from "@/api/types";
import { API_BASE } from "@/config";
import { CategoryIcon } from "@/features/category-icon";
import { innovationHref, metaLine } from "@/features/innovation-row";
import { useVote } from "@/hooks/use-tester";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Sheet } from "@/ui/sheet";
import { Txt } from "@/ui/text";

interface Counts {
  down: number;
  up: number;
}

const voteWords = (count: number) =>
  `${count} ${pluralPl(count, "głos", "głosy", "głosów")}`;

function VoteButton({
  active,
  busy,
  count,
  icon: Icon,
  label,
  onPress,
  worded,
}: {
  active: boolean;
  busy: boolean;
  count: number | null;
  icon: LucideIcon;
  label: string;
  onPress: () => void;
  worded: boolean;
}) {
  const { colors, highContrast, reduceMotion } = useTheme();
  const [hovered, setHovered] = useState(false);
  const ink = active ? colors.onStamp : colors.stamp;
  const rest = hovered ? colors.toneHover : colors.tone;
  return (
    <Pressable
      aria-busy={busy}
      aria-label={count === null ? label : `${label}, ${voteWords(count)}`}
      aria-pressed={active}
      disabled={busy}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={onPress}
      role="button"
      style={({ pressed }) => [
        styles.vote,
        {
          backgroundColor: active ? colors.stamp : rest,
          borderColor: highContrast ? colors.ink : "transparent",
          borderWidth: highContrast ? 2 : 0,
          transform: [{ scale: pressed && !reduceMotion ? 0.95 : 1 }],
        },
      ]}
    >
      {busy ? (
        <ActivityIndicator color={ink} />
      ) : (
        <Icon aria-hidden color={ink} size={22} strokeWidth={2.2} />
      )}
      {worded ? (
        <Txt style={{ color: ink }} variant="detail" weight="600">
          {label}
        </Txt>
      ) : null}
      {count === null ? null : (
        <Txt mono style={{ color: ink }} variant="number">
          {count}
        </Txt>
      )}
    </Pressable>
  );
}

function Votes({
  slug,
  needId,
  initial,
  worded,
}: {
  initial: Counts | null;
  needId?: string;
  slug: string;
  worded: boolean;
}) {
  const vote = useVote(slug, needId, initial ?? undefined);
  const live = vote.counts ?? initial;
  const cast = (kind: FeedbackKind) => () => {
    vote.vote(kind).catch(() => undefined);
  };
  return (
    <View style={styles.votes}>
      <View aria-label="Ocena rozwiązania" role="group" style={styles.voteRow}>
        <VoteButton
          active={vote.mine === "fits"}
          busy={vote.busy === "fits"}
          count={live ? live.up : null}
          icon={ThumbsUp}
          label="Pasuje"
          onPress={cast("fits")}
          worded={worded}
        />
        <VoteButton
          active={vote.mine === "does_not_fit"}
          busy={vote.busy === "does_not_fit"}
          count={live ? live.down : null}
          icon={ThumbsDown}
          label="Nie pasuje"
          onPress={cast("does_not_fit")}
          worded={worded}
        />
      </View>
      <View aria-live="polite">
        {vote.error ? (
          <Txt tone="bad" variant="small" weight="500">
            {vote.error}
          </Txt>
        ) : null}
      </View>
    </View>
  );
}

interface Pictured {
  image_alt?: string | null;
  image_card_url?: string | null;
  image_label?: string | null;
}

const pictureOf = (innovation: InnovationSummary) => {
  const fields = innovation as InnovationSummary & Pictured;
  if (!fields.image_card_url) {
    return null;
  }
  const uri = fields.image_card_url.startsWith("/")
    ? `${API_BASE}${fields.image_card_url}`
    : fields.image_card_url;
  return {
    alt: fields.image_alt ?? "",
    label: fields.image_label ?? null,
    uri,
  };
};

interface InnovationCardProps {
  featured?: boolean;
  index?: number;
  innovation: InnovationSummary;
  needId?: string;
  reason?: string;
}

export function InnovationCard({
  innovation,
  reason,
  index,
  needId,
  featured = false,
}: InnovationCardProps) {
  const { colors, type, wide, reduceMotion } = useTheme();
  const [hovered, setHovered] = useState(false);
  const picture = pictureOf(innovation);
  const titleSize = featured && wide ? type.h2 : type.h3;
  const votes = innovation.votes ?? null;
  return (
    <Sheet raised={featured} style={styles.card}>
      {picture ? (
        <View style={[styles.picture, { backgroundColor: colors.tone }]}>
          <Image
            accessibilityLabel={picture.alt}
            contentFit="cover"
            source={{ uri: picture.uri }}
            style={styles.image}
            transition={reduceMotion ? 0 : 240}
          />
          {index === undefined ? null : (
            <View style={[styles.rank, { backgroundColor: colors.paper }]}>
              <Txt tone="stamp" variant="small" weight="600">
                {`Propozycja ${index}`}
              </Txt>
            </View>
          )}
        </View>
      ) : (
        <View style={styles.head}>
          <View style={[styles.tile, { backgroundColor: colors.tone }]}>
            <CategoryIcon size={26} slug={innovation.category.slug} />
          </View>
          {index === undefined ? null : (
            <Txt tone="stamp" variant="small" weight="600">
              {`Propozycja ${index}`}
            </Txt>
          )}
        </View>
      )}
      <View style={styles.body}>
        <Link asChild href={innovationHref(innovation.slug, needId)}>
          <Pressable
            onHoverIn={() => setHovered(true)}
            onHoverOut={() => setHovered(false)}
            role="link"
          >
            <Txt
              style={{
                color: hovered ? colors.stamp : colors.ink,
                fontSize: titleSize,
                letterSpacing: titleSize * -0.025,
                lineHeight: Math.round(titleSize * 1.15),
              }}
              weight="600"
            >
              {innovation.title}
            </Txt>
          </Pressable>
        </Link>
        <Txt tone="soft" variant={featured ? "body" : "label"}>
          {reason ?? innovation.lead}
        </Txt>
        <Txt tone="soft" variant="small">
          {[metaLine(innovation), picture?.label].filter(Boolean).join(" · ")}
        </Txt>
      </View>
      <View style={styles.foot}>
        <Votes
          initial={votes}
          needId={needId}
          slug={innovation.slug}
          worded={wide || featured}
        />
        <Link asChild href={innovationHref(innovation.slug, needId)}>
          <Pressable
            aria-label={`Zobacz rozwiązanie: ${innovation.title}`}
            role="link"
            style={StyleSheet.flatten([
              styles.open,
              { backgroundColor: featured ? colors.stamp : "transparent" },
            ])}
          >
            <Txt
              style={{ color: featured ? colors.onStamp : colors.stamp }}
              variant="label"
              weight="600"
            >
              Zobacz
            </Txt>
            <ArrowRight
              aria-hidden
              color={featured ? colors.onStamp : colors.stamp}
              size={22}
            />
          </Pressable>
        </Link>
      </View>
    </Sheet>
  );
}

export function CardGrid({ children }: { children: ReactNode[] }) {
  const { wide } = useTheme();
  if (!wide) {
    return <View style={styles.stack}>{children}</View>;
  }
  const rows: ReactNode[][] = [];
  for (let index = 0; index < children.length; index += 2) {
    rows.push(children.slice(index, index + 2));
  }
  return (
    <View style={styles.stack}>
      {rows.map((row, index) => (
        <View
          key={`row-${String(index)}`}
          role="presentation"
          style={styles.gridRow}
        >
          {row.map((cell, cellIndex) => (
            <View key={`cell-${String(cellIndex)}`} style={styles.cell}>
              {cell}
            </View>
          ))}
          {row.length === 1 ? <View style={styles.cell} /> : null}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  body: {
    flexGrow: 1,
    gap: space.sm,
  },
  card: {
    flexGrow: 1,
    gap: space.md + 2,
  },
  cell: {
    flex: 1,
  },
  foot: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.sm,
    justifyContent: "space-between",
  },
  gridRow: {
    alignItems: "stretch",
    flexDirection: "row",
    gap: space.lg,
  },
  head: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  image: {
    height: "100%",
    width: "100%",
  },
  open: {
    alignItems: "center",
    borderRadius: radius.button,
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget + 4,
    paddingHorizontal: space.lg,
  },
  picture: {
    aspectRatio: 16 / 9,
    borderRadius: 20,
    overflow: "hidden",
  },
  rank: {
    alignItems: "center",
    borderRadius: radius.pill,
    justifyContent: "center",
    minHeight: 36,
    paddingHorizontal: space.md,
    position: "absolute",
    right: space.sm + 2,
    top: space.sm + 2,
  },
  stack: {
    gap: space.lg,
  },
  tile: {
    alignItems: "center",
    borderRadius: 16,
    height: 52,
    justifyContent: "center",
    width: 52,
  },
  vote: {
    alignItems: "center",
    borderRadius: radius.pill,
    flexDirection: "row",
    gap: space.sm,
    justifyContent: "center",
    minHeight: minTarget + 4,
    minWidth: 72,
    paddingHorizontal: space.lg,
  },
  voteRow: {
    flexDirection: "row",
    gap: space.sm,
  },
  votes: {
    gap: space.xs,
  },
});
