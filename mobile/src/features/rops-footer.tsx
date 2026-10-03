import { Image } from "expo-image";
import { useEffect, useState } from "react";
import { Linking, Platform, Pressable, StyleSheet, View } from "react-native";
import { API_BASE } from "@/config";
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
  malopolska: require("../../assets/rops/malopolska.png"),
  malopolskaWhite: require("../../assets/rops/malopolska-white.png"),
  rops: require("../../assets/rops/rops.png"),
  ropsWhite: require("../../assets/rops/rops-white.png"),
};

const useDemoData = () => {
  const [demo, setDemo] = useState(false);
  useEffect(() => {
    const abort = new AbortController();
    fetch(`${API_BASE}/api/meta`, { signal: abort.signal })
      .then((response) => (response.ok ? response.json() : null))
      .then((meta: { demo?: boolean } | null) => setDemo(meta?.demo === true))
      .catch(() => setDemo(false));
    return () => abort.abort();
  }, []);
  return demo;
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
  const demo = useDemoData();
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
          source={dark ? logos.malopolskaWhite : logos.malopolska}
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
    height: 24,
    width: 141,
  },
  rops: {
    height: 56,
    width: 173,
  },
});
