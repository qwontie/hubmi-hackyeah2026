export function showTip(
  target: Element | null,
  text: string,
  tone: "ink" | "bad" = "ink"
) {
  if (!(target instanceof HTMLElement)) {
    return;
  }
  for (const old of target.querySelectorAll(":scope > .hm-tip")) {
    old.remove();
  }
  const tip = document.createElement("span");
  tip.className = "hm-tip";
  tip.dataset.tone = tone;
  tip.setAttribute("role", "status");
  tip.textContent = text;
  target.append(tip);
  setTimeout(() => tip.remove(), tone === "bad" ? 4000 : 1800);
}
