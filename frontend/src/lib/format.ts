import type { NeedStatus } from "$lib/api/admin";

const ZONE = "Europe/Warsaw";

export const statusLabel: Record<NeedStatus, string> = {
  answered: "Odpowiedziana",
  closed: "Zamknięta",
  junk: "Nie dotyczy",
  new: "Nowa",
};

export const periodWords: Record<string, string> = {
  "7d": "w 7 dniach",
  "30d": "w 30 dniach",
  "90d": "w 90 dniach",
  "365d": "w roku",
};

export function registerNumber(value: number | null | undefined): string {
  return value === null || value === undefined
    ? ""
    : String(value).padStart(4, "0");
}

export function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("pl-PL", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: ZONE,
  });
}

export function dayWords(iso: string): string {
  return new Date(iso)
    .toLocaleDateString("pl-PL", {
      day: "numeric",
      month: "long",
      timeZone: ZONE,
    })
    .replace(" ", "\u00a0");
}

function dayKey(date: Date): string {
  return date.toLocaleDateString("en-CA", { timeZone: ZONE });
}

export function when(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86_400_000);
  if (dayKey(date) === dayKey(today)) {
    return clock(iso);
  }
  if (dayKey(date) === dayKey(yesterday)) {
    return `wczoraj, ${clock(iso)}`;
  }
  return `${dayWords(iso)}, ${clock(iso)}`;
}

export function powiatName(
  slug: string | null | undefined,
  names: Map<string, string>
): string {
  if (!slug) {
    return "";
  }
  return names.get(slug) ?? slug.replaceAll("-", " ");
}

export function plural(
  n: number,
  one: string,
  few: string,
  many: string
): string {
  if (n === 1) {
    return one;
  }
  const tens = n % 100;
  const units = n % 10;
  if (units >= 2 && units <= 4 && (tens < 12 || tens > 14)) {
    return few;
  }
  return many;
}

export function nbsp(text: string): string {
  return text.replace(/(^|\s)([aiouwzAIOUWZ])\s/g, "$1$2 ");
}
