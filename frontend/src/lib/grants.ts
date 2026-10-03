import type {
  AdminGrantCall,
  ApplicationStatus,
  GrantSection,
} from "$lib/api/admin";
import { dayWords } from "$lib/format";

export const applicationLabel: Record<ApplicationStatus, string> = {
  accepted: "Przyjęty",
  draft: "Wersja robocza",
  in_review: "W ocenie",
  rejected: "Odrzucony",
  submitted: "Złożony",
};

export const reviewStatuses: {
  id: "in_review" | "accepted" | "rejected";
  label: string;
}[] = [
  { id: "in_review", label: "W ocenie" },
  { id: "accepted", label: "Przyjęty" },
  { id: "rejected", label: "Odrzucony" },
];

export function callState(call: AdminGrantCall): string {
  if (call.status === "draft") {
    return "Szkic";
  }
  if (call.status === "cancelled") {
    return "Anulowany";
  }
  if (call.phase === "upcoming") {
    return `Otwiera się ${dayWords(call.opens_at)}`;
  }
  if (call.phase === "open") {
    return `Otwarty do ${dayWords(call.closes_at)}`;
  }
  return `Zamknięty ${dayWords(call.closes_at)}`;
}

export function toLocalInput(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fromLocalInput(value: string): string {
  return new Date(value).toISOString();
}

const NON_KEY = /[^a-z0-9]+/g;
const EDGE_UNDERSCORES = /^_+|_+$/g;
const LEADING_NON_LETTERS = /^[^a-z]+/;
const DIACRITICS = /\p{Diacritic}/gu;
const SMALL_L_STROKE = /ł/g;

export function sectionKey(label: string, taken: Set<string>): string {
  const base =
    label
      .toLocaleLowerCase("pl")
      .normalize("NFD")
      .replace(DIACRITICS, "")
      .replace(SMALL_L_STROKE, "l")
      .replace(NON_KEY, "_")
      .replace(EDGE_UNDERSCORES, "")
      .replace(LEADING_NON_LETTERS, "")
      .slice(0, 36) || "sekcja";
  const padded = base.length < 2 ? `${base}_x` : base;
  let key = padded;
  let n = 2;
  while (taken.has(key)) {
    key = `${padded}_${n}`;
    n += 1;
  }
  return key;
}

export const blankSection = (taken: Set<string>): GrantSection => ({
  hint: "",
  key: sectionKey("sekcja", taken),
  label: "",
  max_length: 2000,
  required: true,
});
