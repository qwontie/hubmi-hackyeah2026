import { Link, usePathname } from "expo-router";
import {
  Accessibility,
  Library,
  type LucideIcon,
  MessageSquareText,
  Search,
} from "lucide-react-native";
import { useState } from "react";
import { Platform, Pressable, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { APP_NAME, ORGANIZATION_NAME } from "@/config";
import { useTheme } from "@/theme/settings";
import { fonts, minTarget, radius, space } from "@/theme/tokens";
import { Txt } from "./text";

interface NavItem {
  href: "/" | "/biblioteka" | "/zgloszenia" | "/dostepnosc";
  icon: LucideIcon;
  label: string;
  short: string;
}

const NAV: NavItem[] = [
  { href: "/", icon: Search, label: "Szukaj rozwiązania", short: "Szukaj" },
  {
    href: "/biblioteka",
    icon: Library,
    label: "Biblioteka",
    short: "Biblioteka",
  },
  {
    href: "/zgloszenia",
    icon: MessageSquareText,
    label: "Moje zgłoszenia",
    short: "Zgłoszenia",
  },
  {
    href: "/dostepnosc",
    icon: Accessibility,
    label: "Dostępność",
    short: "Dostępność",
  },
];

const isActive = (pathname: string, href: string) =>
  href === "/"
    ? pathname === "/" || pathname.startsWith("/innowacje")
    : pathname.startsWith(href);

const tabBackground = (
  colors: { board: string; tab: string; tabHover: string },
  active: boolean,
  hovered: boolean
) => {
  if (active) {
    return colors.board;
  }
  return hovered ? colors.tabHover : colors.tab;
};

function FolderTab({ item }: { item: NavItem }) {
  const { colors, highContrast } = useTheme();
  const pathname = usePathname();
  const [hovered, setHovered] = useState(false);
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  return (
    <Link asChild href={item.href}>
      <Pressable
        aria-current={active ? "page" : undefined}
        onHoverIn={() => setHovered(true)}
        onHoverOut={() => setHovered(false)}
        role="link"
        style={StyleSheet.flatten([
          styles.folderTab,
          {
            backgroundColor: tabBackground(colors, active, hovered),
            borderBottomWidth: 0,
            borderColor: highContrast ? colors.ink : "transparent",
            borderWidth: highContrast ? 2 : 0,
            marginTop: active || hovered ? 0 : 6,
            minHeight: active || hovered ? 56 : 50,
          },
        ])}
      >
        <Icon
          aria-hidden
          color={active ? colors.stamp : colors.tabInkSoft}
          size={20}
          strokeWidth={active ? 2.4 : 2}
        />
        <Txt variant="label" weight={active ? "600" : "500"}>
          {item.label}
        </Txt>
      </Pressable>
    </Link>
  );
}

function BarLink({ item }: { item: NavItem }) {
  const { colors, type } = useTheme();
  const pathname = usePathname();
  const active = isActive(pathname, item.href);
  const Icon = item.icon;
  return (
    <Link asChild href={item.href}>
      <Pressable
        aria-current={active ? "page" : undefined}
        aria-label={item.label}
        role="link"
        style={StyleSheet.flatten([
          styles.barLink,
          { backgroundColor: active ? colors.stampWash : "transparent" },
        ])}
      >
        <Icon
          aria-hidden
          color={active ? colors.stamp : colors.inkSoft}
          size={24}
          strokeWidth={active ? 2.4 : 2}
        />
        <Txt
          numberOfLines={1}
          style={{ fontSize: Math.min(type.small - 2, 16), lineHeight: 18 }}
          tone={active ? "stamp" : "default"}
          variant="small"
          weight={active ? "600" : "500"}
        >
          {item.short}
        </Txt>
      </Pressable>
    </Link>
  );
}

export const useLastTabActive = () => {
  const pathname = usePathname();
  const last = NAV.at(-1);
  return last ? isActive(pathname, last.href) : false;
};

function SkipLink() {
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
        const main = document.querySelector("main");
        const heading = main?.querySelector("h1");
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

function Brand() {
  const { colors, wide } = useTheme();
  return (
    <Link asChild href="/">
      <Pressable
        aria-label={`${APP_NAME}, strona główna`}
        role="link"
        style={styles.brand}
      >
        <View style={[styles.seal, { backgroundColor: colors.stamp }]}>
          <Txt
            style={{ fontFamily: fonts["700"], fontSize: 15, lineHeight: 18 }}
            tone="onStamp"
          >
            Hm
          </Txt>
        </View>
        <View>
          <Txt
            style={{ fontSize: 20, letterSpacing: -0.3, lineHeight: 22 }}
            weight="700"
          >
            {APP_NAME}
          </Txt>
          {wide ? (
            <Txt style={{ fontSize: 14, lineHeight: 18 }} tone="soft">
              {ORGANIZATION_NAME}
            </Txt>
          ) : null}
        </View>
      </Pressable>
    </Link>
  );
}

export function TopBar() {
  const { colors, wide, borderWidth } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View
      role="banner"
      style={[
        styles.top,
        {
          backgroundColor: colors.desk,
          borderBottomColor: colors.rule,
          borderBottomWidth: borderWidth === 1 ? 0 : borderWidth,
          paddingBottom: wide ? 0 : space.sm,
          paddingLeft: wide ? space.xxl : space.md,
          paddingRight: wide ? 14 : space.md,
          paddingTop: insets.top + space.sm,
        },
      ]}
    >
      <SkipLink />
      <Brand />
      {wide ? (
        <View aria-label="Menu główne" role="navigation" style={styles.navRow}>
          {NAV.map((item) => (
            <FolderTab item={item} key={item.href} />
          ))}
        </View>
      ) : null}
    </View>
  );
}

export function BottomBar() {
  const { colors, wide, highContrast } = useTheme();
  const insets = useSafeAreaInsets();
  if (wide) {
    return null;
  }
  return (
    <View
      aria-label="Menu główne"
      role="navigation"
      style={[
        styles.bottom,
        {
          backgroundColor: colors.paper,
          borderTopColor: highContrast ? colors.ink : colors.rule,
          borderTopWidth: highContrast ? 2 : StyleSheet.hairlineWidth,
          paddingBottom: Math.max(insets.bottom, space.xs),
        },
      ]}
    >
      {NAV.map((item) => (
        <BarLink item={item} key={item.href} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  barLink: {
    alignItems: "center",
    borderRadius: radius.md,
    flex: 1,
    gap: 2,
    justifyContent: "center",
    minHeight: 60,
    paddingHorizontal: 2,
  },
  bottom: {
    flexDirection: "row",
    paddingHorizontal: space.xs,
    paddingTop: space.xs,
  },
  brand: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.md,
    minHeight: minTarget,
    paddingRight: space.sm,
  },
  folderTab: {
    alignItems: "center",
    borderTopLeftRadius: radius.tab,
    borderTopRightRadius: radius.tab,
    flexDirection: "row",
    gap: space.sm,
    paddingHorizontal: 18,
  },
  navRow: {
    alignItems: "flex-end",
    alignSelf: "flex-end",
    flexDirection: "row",
    flexShrink: 1,
    gap: 6,
    justifyContent: "flex-end",
  },
  seal: {
    alignItems: "center",
    borderRadius: 10,
    height: 36,
    justifyContent: "center",
    width: 36,
  },
  skip: {
    borderRadius: radius.md,
    left: space.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    position: "absolute",
    zIndex: 10,
  },
  top: {
    alignItems: "center",
    flexDirection: "row",
    gap: space.lg,
    justifyContent: "space-between",
    paddingBottom: space.sm,
  },
});
