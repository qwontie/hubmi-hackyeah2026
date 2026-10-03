import { Platform } from "react-native";
import type { Palette } from "@/theme/tokens";

const STYLE_ID = "hubmi-globals";

export const applyWebGlobals = (colors: Palette, reduceMotion: boolean) => {
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
html, body { background: ${colors.desk}; color: ${colors.ink}; }
body { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
::selection { background: ${colors.stampWash}; color: ${colors.ink}; }
input, textarea { caret-color: ${colors.stamp}; }
textarea::placeholder, input::placeholder { color: ${colors.inkSoft}; opacity: 1; }
*:focus { outline: none; }
*:focus-visible { outline: 2px solid ${colors.ring} !important; outline-offset: 2px !important; }
[tabindex="-1"]:focus-visible { outline: none !important; }
[role="heading"], h1, h2, h3 { scroll-margin-top: 24px; }
textarea:focus-visible, input:focus-visible { outline: none !important; }
select:focus-visible { outline-offset: 1px !important; }
a { text-underline-offset: 0.18em; text-decoration-thickness: 1px; }
a:hover { text-decoration-thickness: 2px; }
* { scrollbar-color: ${colors.ruleStrong} transparent; }
.hubmi-skip { position: absolute; left: 12px; top: -80px; z-index: 10; }
.hubmi-skip:focus { top: 12px; }
${reduceMotion ? "*, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }" : "@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }"}
`;
};
