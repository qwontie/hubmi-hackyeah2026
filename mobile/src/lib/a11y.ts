import { AccessibilityInfo, findNodeHandle, Platform } from "react-native";

const WIDE = 900;
const UNDER_NAV = 160;
const UNDER_PILL = 76;

export const focusElement = (node: unknown) => {
  if (Platform.OS !== "web" || !node) {
    return false;
  }
  const element = node as HTMLElement;
  if (typeof element.focus !== "function") {
    return false;
  }
  if (!element.hasAttribute("tabindex")) {
    element.setAttribute("tabindex", "-1");
  }
  element.style.scrollMarginTop = `${window.innerWidth >= WIDE ? UNDER_NAV : UNDER_PILL}px`;
  element.focus({ preventScroll: false });
  element.scrollIntoView?.({ behavior: "auto", block: "start" });
  return true;
};

export const focusAndAnnounce = (node: unknown, announcement: string) => {
  if (Platform.OS === "web") {
    focusElement(node);
    return;
  }
  const handle = node
    ? findNodeHandle(node as Parameters<typeof findNodeHandle>[0])
    : null;
  if (handle) {
    AccessibilityInfo.setAccessibilityFocus(handle);
  }
  AccessibilityInfo.announceForAccessibility(announcement);
};
