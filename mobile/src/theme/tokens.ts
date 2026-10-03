export interface Palette {
  bad: string;
  desk: string;
  ink: string;
  inkSoft: string;
  ok: string;
  onStamp: string;
  paper: string;
  ring: string;
  rule: string;
  ruleStrong: string;
  stamp: string;
  stampPress: string;
  stampWash: string;
  sunk: string;
  warn: string;
}

export const palettes: Record<"standard" | "contrast", Palette> = {
  contrast: {
    bad: "#9e0f18",
    desk: "#ffffff",
    ink: "#000000",
    inkSoft: "#1d1e29",
    ok: "#004d25",
    onStamp: "#ffffff",
    paper: "#ffffff",
    ring: "#000000",
    rule: "#000000",
    ruleStrong: "#000000",
    stamp: "#24197f",
    stampPress: "#170f5c",
    stampWash: "#e7e9ff",
    sunk: "#ffffff",
    warn: "#6b4100",
  },
  standard: {
    bad: "#c51d28",
    desk: "#ebecf2",
    ink: "#1d1e29",
    inkSoft: "#585a66",
    ok: "#006933",
    onStamp: "#f7f8ff",
    paper: "#fafafc",
    ring: "#544ccb",
    rule: "#dddde3",
    ruleStrong: "#8a8c99",
    stamp: "#4137a6",
    stampPress: "#352795",
    stampWash: "#e7e9ff",
    sunk: "#f2f3f7",
    warn: "#945a00",
  },
};

export const space = {
  lg: 16,
  md: 12,
  sm: 8,
  xl: 24,
  xs: 4,
  xxl: 32,
  xxxl: 48,
} as const;

export const radius = {
  lg: 14,
  md: 10,
  pill: 999,
  sheet: 20,
  sm: 8,
  xs: 5,
} as const;

export const baseType = {
  body: 18,
  detail: 17,
  h1: 34,
  h2: 24,
  h3: 20,
  label: 17,
  lead: 20,
  number: 17,
  small: 16,
  stampWord: 13,
} as const;

export type TypeRole = keyof typeof baseType;

export const fonts = {
  "400": "Geist_400Regular",
  "500": "Geist_500Medium",
  "600": "Geist_600SemiBold",
  "700": "Geist_700Bold",
  mono: "GeistMono_600SemiBold",
} as const;

export type Weight = "400" | "500" | "600" | "700";

export const textScales = [
  { factor: 1, key: "standard", label: "Standardowy" },
  { factor: 1.2, key: "large", label: "Duży" },
  { factor: 1.4, key: "xlarge", label: "Bardzo duży" },
] as const;

export type TextScaleKey = (typeof textScales)[number]["key"];

export const minTarget = 48;
export const contentWidth = 760;
export const wideBreakpoint = 900;
