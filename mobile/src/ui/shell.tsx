import { Link, usePathname } from "expo-router";
import {
  ALargeSmall,
  Library,
  Lightbulb,
  type LucideIcon,
  Map as MapIcon,
  MessageSquareText,
  Search,
} from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { APP_NAME } from "@/config";
import { useChromeTone } from "@/theme/chrome";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Glass } from "./glass";
import { nightAttr } from "./night";
import { Txt } from "./text";

type TabHref = "/" | "/mapa" | "/biblioteka" | "/pomysl" | "/zgloszenia";

export interface TabItem {
  href: TabHref;
  icon: LucideIcon;
  label: string;
  name: string;
  sf: { default: string; selected: string };
}

export const TABS: TabItem[] = [
  {
    href: "/",
    icon: Search,
    label: "Szukaj",
    name: "index",
    sf: { default: "magnifyingglass", selected: "magnifyingglass" },
  },
  {
    href: "/mapa",
    icon: MapIcon,
    label: "Mapa",
    name: "mapa",
    sf: { default: "map", selected: "map.fill" },
  },
  {
    href: "/biblioteka",
    icon: Library,
    label: "Biblioteka",
    name: "biblioteka",
    sf: { default: "books.vertical", selected: "books.vertical.fill" },
  },
  {
    href: "/pomysl",
    icon: Lightbulb,
    label: "Pomysł",
    name: "pomysl",
    sf: { default: "lightbulb", selected: "lightbulb.fill" },
  },
  {
    href: "/zgloszenia",
    icon: MessageSquareText,
    label: "Zgłoszenia",
    name: "zgloszenia",
    sf: { default: "text.bubble", selected: "text.bubble.fill" },
  },
];

const isActive = (pathname: string, href: string) => {
  if (href === "/") {
    return pathname === "/" || pathname.startsWith("/innowacje");
  }
  if (href === "/biblioteka") {
    return (
      pathname.startsWith("/biblioteka") ||
      pathname.startsWith("/wiedza") ||
      pathname.startsWith("/materialy")
    );
  }
  if (href === "/zgloszenia") {
    return pathname.startsWith("/zgloszeni");
  }
  return pathname.startsWith(href);
};

const useChromeInk = () => {
  const { colors } = useTheme();
  const tone = useChromeTone();
  const night = tone === "night";
  return {
    active: night ? colors.onNight : colors.stamp,
    brandNight: tone !== "day",
    night,
    rest: night ? colors.onNightSoft : colors.inkSoft,
    wash: night ? "rgba(252, 252, 255, 0.16)" : colors.tone,
  };
};

function BarLink({ item }: { item: TabItem }) {
  const { highContrast } = useTheme();
  const ink = useChromeInk();
  const pathname = usePathname();
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  const color = active ? ink.active : ink.rest;
  return (
    <Link asChild href={item.href}>
      <Pressable
        aria-current={active ? "page" : undefined}
        aria-label={item.label}
        role="link"
        style={StyleSheet.flatten([
          styles.barLink,
          {
            backgroundColor: active ? ink.wash : "transparent",
            borderColor: active && highContrast ? color : "transparent",
            borderWidth: highContrast ? 2 : 0,
          },
        ])}
      >
        <Icon
          aria-hidden
          color={color}
          size={24}
          strokeWidth={active ? 2.4 : 2}
        />
        <Txt
          maxFontSizeMultiplier={1.15}
          numberOfLines={1}
          style={[styles.barLabel, { color }]}
          weight="600"
        >
          {item.label}
        </Txt>
      </Pressable>
    </Link>
  );
}

export function TabBar() {
  const { wide } = useTheme();
  const { night } = useChromeInk();
  const insets = useSafeAreaInsets();
  if (wide) {
    return null;
  }
  return (
    <View
      pointerEvents="box-none"
      style={[styles.dock, { bottom: Math.max(insets.bottom, 14) }]}
    >
      <Glass
        aria-label="Menu główne"
        night={night}
        role="navigation"
        style={styles.bar}
        {...nightAttr(night)}
      >
        {TABS.map((item) => (
          <BarLink item={item} key={item.href} />
        ))}
      </Glass>
    </View>
  );
}

export function Brand({ night = false }: { night?: boolean }) {
  const { colors } = useTheme();
  return (
    <Link asChild href="/">
      <Pressable
        aria-label={`${APP_NAME}, strona główna`}
        role="link"
        style={styles.brand}
      >
        <View
          style={[
            styles.seal,
            { backgroundColor: night ? colors.onNight : colors.stamp },
          ]}
        >
          <Txt
            style={[
              styles.sealText,
              { color: night ? colors.night : colors.onStamp },
            ]}
            weight="700"
          >
            Hm
          </Txt>
        </View>
        <Txt
          style={[
            styles.brandName,
            { color: night ? colors.onNight : colors.ink },
          ]}
          weight="600"
        >
          {APP_NAME}
        </Txt>
        <Txt
          style={[
            styles.brandOrg,
            { color: night ? colors.onNightSoft : colors.inkSoft },
          ]}
        >
          ROPS Kraków
        </Txt>
      </Pressable>
    </Link>
  );
}

export function AccessButton({ night = false }: { night?: boolean }) {
  const { colors, wide } = useTheme();
  if (wide) {
    return null;
  }
  return (
    <Link asChild href="/dostepnosc">
      <Pressable
        aria-label="Dostępność: wielkość tekstu i kontrast"
        role="link"
        style={styles.round}
      >
        <Glass interactive night={night} style={styles.roundGlass}>
          <ALargeSmall
            aria-hidden
            color={night ? colors.onNight : colors.ink}
            size={26}
            strokeWidth={2}
          />
        </Glass>
      </Pressable>
    </Link>
  );
}

function WideLink({
  href,
  icon: Icon,
  label,
}: {
  href: TabHref | "/dostepnosc";
  icon: LucideIcon;
  label: string;
}) {
  const { highContrast } = useTheme();
  const ink = useChromeInk();
  const pathname = usePathname();
  const [hovered, setHovered] = useState(false);
  const active = isActive(pathname, href);
  const color = active || hovered ? ink.active : ink.rest;
  return (
    <Link asChild href={href}>
      <Pressable
        aria-current={active ? "page" : undefined}
        onHoverIn={() => setHovered(true)}
        onHoverOut={() => setHovered(false)}
        role="link"
        style={StyleSheet.flatten([
          styles.wideLink,
          {
            backgroundColor: active ? ink.wash : "transparent",
            borderColor: active && highContrast ? color : "transparent",
            borderWidth: highContrast ? 2 : 0,
          },
        ])}
      >
        <Icon
          aria-hidden
          color={color}
          size={20}
          strokeWidth={active ? 2.4 : 2}
        />
        <Txt style={[styles.wideLabel, { color }]} weight="600">
          {label}
        </Txt>
      </Pressable>
    </Link>
  );
}

export function WideChrome() {
  const { wide } = useTheme();
  const { night, brandNight } = useChromeInk();
  if (!wide) {
    return null;
  }
  return (
    <View pointerEvents="box-none" style={styles.wide} {...nightAttr(night)}>
      <Brand night={brandNight} />
      <Glass
        aria-label="Menu główne"
        night={night}
        role="navigation"
        style={styles.wideNav}
      >
        {TABS.map((item) => (
          <WideLink
            href={item.href}
            icon={item.icon}
            key={item.href}
            label={item.label}
          />
        ))}
        <WideLink href="/dostepnosc" icon={ALargeSmall} label="Dostępność" />
      </Glass>
    </View>
  );
}

export function SkipLink() {
  const { colors } = useTheme();
  const [visible, setVisible] = useState(false);
  if (Platform.OS !== "web") {
    return null;
  }
  return (
    <Pressable
      onBlur={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onPress={() => {
        const main = document.querySelector('[role="main"]');
        const heading = document.querySelector('[role="heading"]');
        const target = (heading ?? main) as HTMLElement | null;
        if (target) {
          target.setAttribute("tabindex", "-1");
          target.focus();
        }
      }}
      role="link"
      style={[
        styles.skip,
        {
          backgroundColor: colors.stamp,
          top: visible ? space.sm : -200,
        },
      ]}
    >
      <Txt tone="onStamp" weight="600">
        Przejdź do treści
      </Txt>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    borderRadius: 34,
    flexDirection: "row",
    height: 68,
    padding: 5,
    width: "100%",
  },
  barLabel: {
    fontSize: 12.5,
    letterSpacing: -0.2,
    lineHeight: 16,
  },
  barLink: {
    alignItems: "center",
    borderRadius: 29,
    flex: 1,
    gap: 2,
    justifyContent: "center",
    minHeight: minTarget,
  },
  brand: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.sm + 2,
    minHeight: minTarget,
  },
  brandName: {
    fontSize: 19,
    letterSpacing: -0.2,
    lineHeight: 24,
  },
  brandOrg: {
    fontSize: 18,
    lineHeight: 24,
  },
  dock: {
    left: space.md,
    position: "absolute",
    right: space.md,
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
  seal: {
    alignItems: "center",
    borderRadius: 10,
    height: 34,
    justifyContent: "center",
    width: 34,
  },
  sealText: {
    fontSize: 14,
    lineHeight: 18,
  },
  skip: {
    borderRadius: radius.md,
    left: space.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    position: "absolute",
    zIndex: 30,
  },
  wide: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    left: 0,
    paddingHorizontal: 40,
    position: "absolute",
    right: 0,
    top: 24,
    zIndex: 20,
  },
  wideLabel: {
    fontSize: 16,
    lineHeight: 20,
  },
  wideLink: {
    alignItems: "center",
    borderRadius: 23,
    flexDirection: "row",
    gap: space.sm,
    minHeight: minTarget,
    paddingHorizontal: space.lg + 2,
  },
  wideNav: {
    borderRadius: 28,
    flexDirection: "row",
    padding: 5,
  },
});
