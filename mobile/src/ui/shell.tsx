import { Image } from "expo-image";
import { Link, usePathname } from "expo-router";
import {
  ALargeSmall,
  HandHeart,
  Library,
  type LucideIcon,
  MessageSquareText,
  Search,
} from "lucide-react-native";
import { useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { APP_NAME } from "@/config";
import { A11yButton, A11yPanel, useA11yInline } from "@/features/a11y-controls";
import { focusElement } from "@/lib/a11y";
import { useChromeTone } from "@/theme/chrome";
import { useTheme } from "@/theme/settings";
import { minTarget, radius, space } from "@/theme/tokens";
import { Glass } from "./glass";
import { nightAttr } from "./night";
import { Txt } from "./text";

type TabHref = "/" | "/biblioteka" | "/dzialaj" | "/zgloszenia";

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
    href: "/biblioteka",
    icon: Library,
    label: "Biblioteka",
    name: "biblioteka",
    sf: { default: "books.vertical", selected: "books.vertical.fill" },
  },
  {
    href: "/dzialaj",
    icon: HandHeart,
    label: "Działaj",
    name: "dzialaj",
    sf: { default: "hand.raised", selected: "hand.raised.fill" },
  },
  {
    href: "/zgloszenia",
    icon: MessageSquareText,
    label: "Zgłoszenia",
    name: "zgloszenia",
    sf: { default: "text.bubble", selected: "text.bubble.fill" },
  },
];

const CONTRIBUTE_PATHS = [
  "/dzialaj",
  "/pomysl",
  "/problemy",
  "/nabory",
  "/wolontariat",
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
  if (href === "/dzialaj") {
    return CONTRIBUTE_PATHS.some((path) => pathname.startsWith(path));
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

const marks = {
  signet: require("../../assets/brand/rops-signet.svg"),
  signetWhite: require("../../assets/brand/rops-signet-white.svg"),
};

export function Brand({ night = false }: { night?: boolean }) {
  const { colors, dark } = useTheme();
  const { width } = useWindowDimensions();
  return (
    <Link asChild href="/">
      <Pressable
        aria-label={`${APP_NAME} ROPS Kraków, strona główna`}
        role="link"
        style={styles.brand}
      >
        <Image
          aria-hidden
          contentFit="contain"
          source={night || dark ? marks.signetWhite : marks.signet}
          style={styles.signet}
        />
        <Txt
          maxFontSizeMultiplier={1.3}
          style={[
            styles.brandName,
            { color: night ? colors.onNight : colors.ink },
          ]}
          weight="600"
        >
          {APP_NAME}
        </Txt>
        {width >= 1040 || width < 900 ? (
          <Txt
            maxFontSizeMultiplier={1.3}
            style={[
              styles.brandOrg,
              { color: night ? colors.onNightSoft : colors.inkSoft },
            ]}
          >
            ROPS Kraków
          </Txt>
        ) : null}
      </Pressable>
    </Link>
  );
}

export function AccessButton({ night = false }: { night?: boolean }) {
  return <A11yButton night={night} />;
}

function WideA11y() {
  const { colors } = useTheme();
  const { night } = useChromeInk();
  const [open, setOpen] = useState(false);
  const ink = night ? colors.onNight : colors.ink;
  return (
    <>
      <Pressable
        aria-expanded={open}
        onPress={() => setOpen(true)}
        role="button"
        style={styles.a11yPress}
      >
        <Glass interactive night={night} style={styles.a11y}>
          <ALargeSmall aria-hidden color={ink} size={22} strokeWidth={2} />
          <Txt style={[styles.wideLabel, { color: ink }]} weight="600">
            Dostępność
          </Txt>
        </Glass>
      </Pressable>
      <A11yPanel onClose={() => setOpen(false)} open={open} />
    </>
  );
}

function WideLink({
  href,
  icon: Icon,
  label,
}: {
  href: TabHref;
  icon: LucideIcon;
  label: string;
}) {
  const { highContrast } = useTheme();
  const { width } = useWindowDimensions();
  const tight = width < 1200;
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
          tight && styles.wideLinkTight,
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
  const inline = useA11yInline();
  if (!wide) {
    return null;
  }
  return (
    <View pointerEvents="box-none" style={styles.wide} {...nightAttr(night)}>
      <Brand night={brandNight} />
      <View style={styles.wideRight}>
        {inline ? null : <WideA11y />}
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
        </Glass>
      </View>
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
        focusElement(heading ?? main);
      }}
      role="button"
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
  a11y: {
    alignItems: "center",
    borderRadius: 28,
    flexDirection: "row",
    gap: space.sm,
    minHeight: 58,
    paddingHorizontal: space.lg + 2,
  },
  a11yPress: {
    borderRadius: 28,
  },
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
    textAlign: "center",
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
  signet: {
    height: 30,
    width: 39,
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
    gap: space.lg,
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
  wideLinkTight: {
    gap: 6,
    paddingHorizontal: space.sm + 2,
  },
  wideNav: {
    borderRadius: 28,
    flexDirection: "row",
    flexShrink: 1,
    overflow: "hidden",
    padding: 5,
  },
  wideRight: {
    alignItems: "center",
    flexDirection: "row",
    flexShrink: 1,
    gap: space.md,
  },
});
