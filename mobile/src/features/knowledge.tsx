import { Link } from "expo-router";
import { ChevronRight, FileText } from "lucide-react-native";
import { useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import type { ChallengeSummary, Figure, MaterialSummary } from "@/api/types";
import {
  AI_SUMMARY_NOTE,
  figureSource,
  fileLabel,
  NATIONAL_NOTE,
} from "@/hooks/use-knowledge";
import { useTheme } from "@/theme/settings";
import { radius, space } from "@/theme/tokens";
import { ExternalLink } from "@/ui/external-link";
import { Txt } from "@/ui/text";

export function FigureView({ figure }: { figure: Figure }) {
  const { colors, type } = useTheme();
  const source = figureSource(figure);
  return (
    <View style={[styles.figure, { backgroundColor: colors.sunk }]}>
      <View style={styles.figureHead}>
        <Txt
          style={{
            fontSize: type.h2,
            fontVariant: ["tabular-nums"],
            letterSpacing: type.h2 * -0.03,
            lineHeight: Math.round(type.h2 * 1.2),
          }}
          tone="stamp"
          weight="600"
        >
          {figure.value}
        </Txt>
        <Txt style={styles.flex} weight="500">
          {figure.label}
        </Txt>
      </View>
      <Txt tone="soft" variant="detail">
        {[
          figure.year ? `Rok ${figure.year}` : null,
          figure.scope === "Polska" ? NATIONAL_NOTE : `Zasięg: ${figure.scope}`,
        ]
          .filter(Boolean)
          .join(" · ")}
      </Txt>
      <ExternalLink href={source.url} icon={FileText} label={source.label} />
    </View>
  );
}

function RowLink({
  href,
  children,
}: {
  href:
    | { pathname: "/wiedza/[slug]"; params: { slug: string } }
    | { pathname: "/materialy/[id]"; params: { id: string } };
  children: React.ReactNode;
}) {
  const { colors } = useTheme();
  const [hovered, setHovered] = useState(false);
  return (
    <Link asChild href={href}>
      <Pressable
        onHoverIn={() => setHovered(true)}
        onHoverOut={() => setHovered(false)}
        role="link"
        style={StyleSheet.flatten([
          styles.row,
          { backgroundColor: hovered ? colors.stampWash : "transparent" },
        ])}
      >
        <View style={[styles.flex, styles.rowBody]}>{children}</View>
        <ChevronRight
          aria-hidden
          color={hovered ? colors.stamp : colors.inkSoft}
          size={24}
        />
      </Pressable>
    </Link>
  );
}

export function ChallengeRow({
  challenge,
  last,
}: {
  challenge: ChallengeSummary;
  last: boolean;
}) {
  const { colors } = useTheme();
  const [figure] = challenge.figures;
  return (
    <View
      role="listitem"
      style={[
        styles.item,
        !last && { borderBottomColor: colors.rule, borderBottomWidth: 1 },
      ]}
    >
      <RowLink
        href={{ params: { slug: challenge.slug }, pathname: "/wiedza/[slug]" }}
      >
        <Txt variant="h3" weight="600">
          {challenge.title}
        </Txt>
        {challenge.summary ? <Txt>{challenge.summary}</Txt> : null}
        <Txt tone="soft" variant="detail">
          {[
            challenge.area.name,
            figure
              ? `${figure.label}: ${figure.value}${figure.scope === "Polska" ? " (Polska)" : ""}`
              : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </Txt>
      </RowLink>
    </View>
  );
}

export function MaterialRow({
  material,
  last,
}: {
  material: MaterialSummary;
  last: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View
      role="listitem"
      style={[
        styles.item,
        !last && { borderBottomColor: colors.rule, borderBottomWidth: 1 },
      ]}
    >
      <RowLink
        href={{ params: { id: material.id }, pathname: "/materialy/[id]" }}
      >
        <Txt variant="h3" weight="600">
          {material.title}
        </Txt>
        {material.summary ? (
          <Txt numberOfLines={3}>{material.summary}</Txt>
        ) : null}
        <Txt tone="soft" variant="detail">
          {[
            material.kind.name,
            material.year ? String(material.year) : null,
            fileLabel(material),
            material.summary && material.summary_ai ? AI_SUMMARY_NOTE : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </Txt>
      </RowLink>
    </View>
  );
}

const styles = StyleSheet.create({
  figure: {
    borderRadius: radius.lg,
    gap: space.sm,
    padding: space.lg,
  },
  figureHead: {
    alignItems: "baseline",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.md,
  },
  flex: {
    flex: 1,
  },
  item: {
    paddingVertical: space.xs,
  },
  row: {
    alignItems: "flex-start",
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: space.md,
    marginHorizontal: -space.sm,
    paddingHorizontal: space.sm,
    paddingVertical: space.md,
  },
  rowBody: {
    gap: space.xs + 2,
  },
});
