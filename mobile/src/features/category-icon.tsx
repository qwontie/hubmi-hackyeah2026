import {
  Accessibility,
  Baby,
  Brain,
  BriefcaseBusiness,
  Coins,
  Ear,
  HandHeart,
  HeartPulse,
  House,
  Languages,
  type LucideIcon,
  Shapes,
  Users,
} from "lucide-react-native";
import { StyleSheet, View } from "react-native";
import { useTheme } from "@/theme/settings";

const ICONS: Record<string, LucideIcon> = {
  bezdomnosc: House,
  cudzoziemcy: Languages,
  "dla-cudzoziemcow": Languages,
  "dla-dzieci-mlodziezy-i-rodziny": Baby,
  "dla-osob-o-ograniczonej-mobilnosci": Accessibility,
  "dla-osob-w-kryzysie-bezdomnosci": House,
  "dla-osob-z-niepelnosprawnoscia-intelektualna": Brain,
  "dla-osob-z-niepelnosprawnoscia-sensoryczna": Ear,
  "dla-rynku-pracy": BriefcaseBusiness,
  "dla-seniorow": HandHeart,
  "dla-zdrowia-i-medycyny": HeartPulse,
  niepelnosprawnosc: Accessibility,
  "rodzina-i-piecza": Users,
  seniorzy: HandHeart,
  ubostwo: Coins,
  zdrowie: HeartPulse,
  "zdrowie-psychiczne": Brain,
};

export const categoryIcon = (slug: string | null | undefined): LucideIcon =>
  (slug ? ICONS[slug] : undefined) ?? Shapes;

interface CategoryIconProps {
  color?: string;
  size?: number;
  slug: string | null | undefined;
}

export function CategoryIcon({ slug, size = 22, color }: CategoryIconProps) {
  const { colors } = useTheme();
  const Icon = categoryIcon(slug);
  return (
    <Icon
      aria-hidden
      color={color ?? colors.stamp}
      size={size}
      strokeWidth={2}
    />
  );
}

export function CategoryTile({
  slug,
  size = 56,
}: {
  size?: number;
  slug: string | null | undefined;
}) {
  const { colors, highContrast } = useTheme();
  return (
    <View
      style={[
        styles.tile,
        {
          backgroundColor: colors.paper,
          borderColor: highContrast ? colors.ink : "transparent",
          borderRadius: Math.round(size * 0.3),
          borderWidth: highContrast ? 2 : 0,
          height: size,
          width: size,
        },
      ]}
    >
      <CategoryIcon size={Math.round(size * 0.5)} slug={slug} />
    </View>
  );
}

const styles = StyleSheet.create({
  tile: {
    alignItems: "center",
    justifyContent: "center",
  },
});
