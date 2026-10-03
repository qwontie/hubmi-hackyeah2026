import { Image } from "expo-image";
import { useState } from "react";
import { Linking, Platform, Pressable, StyleSheet, View } from "react-native";
import { useMeta } from "@/hooks/use-meta";
import { useTheme } from "@/theme/settings";
import { minTarget, space } from "@/theme/tokens";
import { Txt } from "@/ui/text";

const ROPS = "https://rops.krakow.pl";

const LINKS = [
  { href: `${ROPS}/o-rops/zadania`, label: "O ROPS" },
  {
    href: `${ROPS}/innowacje-spoleczne/biblioteka-innowacji-spolecznych/kategorie`,
    label: "Biblioteka innowacji ROPS",
  },
  {
    href: `${ROPS}/kontakt/regionalny-osrodek-polityki-spolecznej-w-krakowie`,
    label: "Kontakt",
  },
  { href: `${ROPS}/polityka-prywatnosci`, label: "Polityka prywatności" },
];

const FOOTER_NOTE =
  "HubMi to prototyp Małopolskiego Hubu Innowacji Społecznych. Regionalny Ośrodek Polityki Społecznej w Krakowie, ul.\u00a0Piastowska\u00a032, 30-070\u00a0Kraków.";

const logos = {
  malopolska: require("../../assets/brand/malopolska.svg"),
  malopolskaBlack: require("../../assets/brand/malopolska-black.svg"),
  malopolskaWhite: require("../../assets/brand/malopolska-white.svg"),
  rops: require("../../assets/brand/rops-logo.svg"),
  ropsWhite: require("../../assets/brand/rops-logo-white.svg"),
};

const malopolskaMark = (dark: boolean, highContrast: boolean) => {
  if (highContrast) {
    return logos.malopolskaBlack;
  }
  return dark ? logos.malopolskaWhite : logos.malopolska;
};

function FooterLink({ href, label }: { href: string; label: string }) {
  const [hovered, setHovered] = useState(false);
  const webProps =
    Platform.OS === "web"
      ? { href, hrefAttrs: { rel: "noopener noreferrer", target: "_blank" } }
      : {};
  return (
    <Pressable
      accessibilityHint="Otwiera się w nowym oknie"
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      onPress={
        Platform.OS === "web"
          ? undefined
          : () => {
              Linking.openURL(href).catch(() => undefined);
            }
      }
      role="link"
      style={styles.link}
      {...webProps}
    >
      <Txt
        style={{ textDecorationLine: hovered ? "underline" : "none" }}
        tone="stamp"
        variant="detail"
        weight="600"
      >
        {label}
      </Txt>
    </Pressable>
  );
}

export function RopsFooter() {
  const { colors, dark, highContrast } = useTheme();
  const meta = useMeta();
  const demo = meta.state.kind === "done" && meta.state.data.demo === true;
  return (
    <View
      aria-label="O serwisie"
      role="group"
      style={[
        styles.footer,
        { borderTopColor: highContrast ? colors.ink : colors.rule },
      ]}
    >
      <View style={styles.logos}>
        <Image
          accessibilityLabel="Regionalny Ośrodek Polityki Społecznej w Krakowie, instytucja Województwa Małopolskiego"
          contentFit="contain"
          source={dark ? logos.ropsWhite : logos.rops}
          style={styles.rops}
        />
        <Image
          accessibilityLabel="Małopolska"
          contentFit="contain"
          source={malopolskaMark(dark, highContrast)}
          style={styles.malopolska}
        />
      </View>
      <Txt tone="soft" variant="detail">
        {FOOTER_NOTE}
      </Txt>
      <View style={styles.links}>
        {LINKS.map((link) => (
          <FooterLink href={link.href} key={link.href} label={link.label} />
        ))}
      </View>
      {demo ? (
        <Txt tone="soft" variant="small">
          Liczby, zgłoszenia i głosy na tej stronie to dane pokazowe.
        </Txt>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    borderTopWidth: 1,
    gap: space.md,
    marginTop: space.xxl,
    paddingTop: space.xl,
  },
  link: {
    justifyContent: "center",
    minHeight: minTarget,
  },
  links: {
    columnGap: space.xl,
    flexDirection: "row",
    flexWrap: "wrap",
  },
  logos: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: space.xl,
  },
  malopolska: {
    height: 22,
    width: 160,
  },
  rops: {
    height: 63,
    width: 200,
  },
});
