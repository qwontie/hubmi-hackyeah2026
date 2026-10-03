import { Platform } from "react-native";
import type { Palette } from "@/theme/tokens";

const STYLE_ID = "hubmi-globals";

export const applyWebGlobals = (
  colors: Palette,
  reduceMotion: boolean,
  night = false
) => {
  if (Platform.OS !== "web" || typeof document === "undefined") {
    return;
  }
  document.documentElement.lang = "pl";
  let style = document.getElementById(STYLE_ID);
  if (!style) {
    style = document.createElement("style");
    style.id = STYLE_ID;
    document.head.appendChild(style);
  }
  style.textContent = `
html, body { background: ${night ? colors.night : colors.ground}; color: ${colors.ink}; }
body { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
::selection { background: ${colors.stampWash}; color: ${colors.ink}; }
input, textarea { caret-color: ${colors.stamp}; }
textarea::placeholder, input::placeholder { opacity: 1; }
*:focus { outline: none; }
*:focus-visible { outline: 2px solid ${colors.ring} !important; outline-offset: 3px !important; }
[data-night] *:focus-visible, [data-night]:focus-visible { outline-color: ${colors.onNight} !important; }
[tabindex="-1"]:focus-visible { outline: none !important; }
[role="heading"], h1, h2, h3 { scroll-margin-top: 24px; }
[role="heading"][aria-level="1"], #results-title { scroll-margin-top: 100vh; }
[role="heading"] { text-wrap: balance; }
[dir="auto"] { text-wrap: pretty; }
textarea:focus-visible, input:focus-visible { outline: none !important; }
select:focus-visible { outline-offset: 1px !important; }
a { text-underline-offset: 0.18em; text-decoration-thickness: 1px; }
a:hover { text-decoration-thickness: 2px; }
* { scrollbar-color: ${colors.ruleStrong} transparent; }
.hubmi-skip { position: absolute; left: 12px; top: -80px; z-index: 10; }
.hubmi-skip:focus { top: 12px; }
@media (forced-colors: active) {
  [role="button"], [role="link"], [role="checkbox"], [role="tab"], a[href] { outline: 1px solid ButtonText; outline-offset: -1px; }
  svg [stroke]:not([stroke="none"]) { stroke: CanvasText !important; }
}
${reduceMotion ? "*, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }" : "@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }"}
`;
};
