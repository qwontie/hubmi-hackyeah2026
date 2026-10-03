export interface Palette {
  bad: string;
  board: string;
  desk: string;
  dusk: string;
  glass: string;
  glassEdge: string;
  glassNight: string;
  glassNightEdge: string;
  ground: string;
  horizon: string;
  ink: string;
  inkSoft: string;
  night: string;
  nightDeep: string;
  nightRise: string;
  ok: string;
  onNight: string;
  onNightSoft: string;
  onStamp: string;
  paper: string;
  ring: string;
  rule: string;
  ruleStrong: string;
  shadow: string;
  stamp: string;
  stampPress: string;
  stampWash: string;
  sun: string;
  sunk: string;
  tab: string;
  tabHover: string;
  tabInkSoft: string;
  tone: string;
  toneHover: string;
  warn: string;
}

export type PaletteKey = "standard" | "dark" | "contrast";

export const palettes: Record<PaletteKey, Palette> = {
  contrast: {
    bad: "#9e0f18",
    board: "#ffffff",
    desk: "#ffffff",
    dusk: "#1d1470",
    glass: "#ffffff",
    glassEdge: "#000000",
    glassNight: "#000000",
    glassNightEdge: "#ffffff",
    ground: "#ffffff",
    horizon: "#24197f",
    ink: "#000000",
    inkSoft: "#131328",
    night: "#0b0635",
    nightDeep: "#000000",
    nightRise: "#170f5c",
    ok: "#004d25",
    onNight: "#ffffff",
    onNightSoft: "#ffffff",
    onStamp: "#ffffff",
    paper: "#ffffff",
    ring: "#000000",
    rule: "#000000",
    ruleStrong: "#000000",
    shadow: "#000000",
    stamp: "#24197f",
    stampPress: "#170f5c",
    stampWash: "#dadbfc",
    sun: "#24197f",
    sunk: "#ffffff",
    tab: "#ffffff",
    tabHover: "#dadbfc",
    tabInkSoft: "#000000",
    tone: "#ffffff",
    toneHover: "#dadbfc",
    warn: "#6b4100",
  },
  dark: {
    bad: "#f97770",
    board: "#0f101e",
    desk: "#0f101e",
    dusk: "#191048",
    glass: "rgba(26, 27, 45, 0.78)",
    glassEdge: "rgba(237, 237, 246, 0.16)",
    glassNight: "rgba(3, 3, 18, 0.72)",
    glassNightEdge: "rgba(237, 237, 246, 0.16)",
    ground: "#0f101e",
    horizon: "#1f1656",
    ink: "#ededf6",
    inkSoft: "#b8b8d1",
    night: "#090623",
    nightDeep: "#030312",
    nightRise: "#130c3a",
    ok: "#5ccb89",
    onNight: "#ededf6",
    onNightSoft: "#c6c7eb",
    onStamp: "#13122c",
    paper: "#1a1b2d",
    ring: "#b7b9ff",
    rule: "#2b2b41",
    ruleStrong: "#6c6d94",
    shadow: "#000000",
    stamp: "#b1b4ff",
    stampPress: "#9fa1f5",
    stampWash: "#272748",
    sun: "#312878",
    sunk: "#141526",
    tab: "#272748",
    tabHover: "#313056",
    tabInkSoft: "#b8b8d1",
    tone: "#272748",
    toneHover: "#313056",
    warn: "#eeb154",
  },
  standard: {
    bad: "#c51d28",
    board: "#eeeeff",
    desk: "#eeeeff",
    dusk: "#4137a6",
    glass: "rgba(252, 252, 255, 0.78)",
    glassEdge: "rgba(255, 255, 255, 0.8)",
    glassNight: "rgba(17, 9, 56, 0.72)",
    glassNightEdge: "rgba(252, 252, 255, 0.22)",
    ground: "#eeeeff",
    horizon: "#5751bd",
    ink: "#131328",
    inkSoft: "#464862",
    night: "#211161",
    nightDeep: "#110938",
    nightRise: "#301f82",
    ok: "#006933",
    onNight: "#fcfcff",
    onNightSoft: "#dadbfc",
    onStamp: "#fcfcff",
    paper: "#fcfcff",
    ring: "#544ccb",
    rule: "#cccdf4",
    ruleStrong: "#7475a3",
    shadow: "#2a2073",
    stamp: "#4137a6",
    stampPress: "#332492",
    stampWash: "#dadbfc",
    sun: "#7574cb",
    sunk: "#f6f6ff",
    tab: "#dadbfc",
    tabHover: "#cfcffb",
    tabInkSoft: "#464862",
    tone: "#dadbfc",
    toneHover: "#cfcffb",
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
  band: 36,
  board: 30,
  button: 20,
  field: 28,
  lg: 18,
  md: 14,
  pill: 999,
  sheet: 30,
  sm: 10,
  tab: 16,
  xs: 6,
} as const;

export const baseType = {
  body: 19,
  detail: 17,
  display: 50,
  h1: 42,
  h2: 30,
  h3: 22,
  label: 18,
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

export const motion = {
  dawn: 1000,
  quick: 150,
  rise: 560,
  settle: 320,
  stagger: 70,
  stamp: 420,
  sunrise: 1700,
} as const;

export const textScales = [
  { factor: 1, key: "standard", label: "Standardowy" },
  { factor: 1.2, key: "large", label: "Duży" },
  { factor: 1.4, key: "xlarge", label: "Bardzo duży" },
] as const;

export type TextScaleKey = (typeof textScales)[number]["key"];

export const minTarget = 48;
export const contentWidth = 760;
export const wideBreakpoint = 900;
export const tabBarSpace = 108;
