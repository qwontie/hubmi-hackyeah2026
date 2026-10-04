import { ShieldCheck } from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import type { InnovationSummary } from "@/api/types";
import { pluralPl } from "@/lib/plural";
import { useTheme } from "@/theme/settings";
import { space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

export const VOLUNTEER_CHECKED = "Sprawdzone przez wolontariuszy";

export const isVolunteerChecked = (innovation: InnovationSummary) =>
  innovation.volunteer_checked === true;

const reportWords = (count: number) =>
  `${count} ${pluralPl(count, "raport", "raporty", "raportów")}`;

export const volunteerReports = (innovation: InnovationSummary) => {
  const reports = innovation.volunteer_reports ?? 0;
  return isVolunteerChecked(innovation) && reports > 0
    ? `${reportWords(reports)} wolontariuszy`
    : null;
};

export function VolunteerBadge({
  innovation,
}: {
  innovation: InnovationSummary;
}) {
  const { colors, type } = useTheme();
  if (!isVolunteerChecked(innovation)) {
    return null;
  }
  const iconSize = Math.round(type.small * 1.15);
  return (
    <View style={styles.badge}>
      <ShieldCheck
        aria-hidden
        color={colors.stamp}
        size={iconSize}
        strokeWidth={2.2}
        style={styles.icon}
      />
      <Txt style={styles.text} tone="stamp" variant="small" weight="600">
        {VOLUNTEER_CHECKED}
      </Txt>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: space.xs + 2,
  },
  icon: {
    marginTop: 2,
  },
  text: {
    flexShrink: 1,
  },
});
