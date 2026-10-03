import type {
  AdminFeedback,
  AdminTestSignup,
  SignupStatus,
} from "$lib/api/admin";

export const whoLabel: Record<AdminTestSignup["who"], string> = {
  expert: "Ekspert lub ekspertka",
  local_government: "Samorząd",
  ngo: "Organizacja pozarządowa",
  resident: "Mieszkaniec lub mieszkanka",
};

export const signupStatuses: { id: SignupStatus; label: string }[] = [
  { id: "new", label: "Nowe" },
  { id: "contacted", label: "Po kontakcie" },
  { id: "closed", label: "Zamknięte" },
];

export const signupLabel: Record<SignupStatus, string> = {
  closed: "Zamknięte",
  contacted: "Po kontakcie",
  new: "Nowe",
};

export const kindLabel: Record<AdminFeedback["kind"], string> = {
  does_not_fit: "Nie pasuje",
  fits: "Pasuje",
  improvement: "Usprawnienie",
};

export const contactKey = (email: string) => email.trim().toLocaleLowerCase();

export const fold = (text: string) =>
  text
    .toLocaleLowerCase("pl")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "");
