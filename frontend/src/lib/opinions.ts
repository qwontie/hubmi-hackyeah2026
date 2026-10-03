import type { AdminFeedback, AdminTestSignup } from "$lib/api/admin";
import { volunteerLabel, volunteerStatuses } from "$lib/volunteers";

export const whoLabel: Record<AdminTestSignup["who"], string> = {
  expert: "Ekspert lub ekspertka",
  local_government: "Samorząd",
  ngo: "Organizacja pozarządowa",
  resident: "Mieszkaniec lub mieszkanka",
};

export const signupStatuses = volunteerStatuses;

export const signupLabel = volunteerLabel;

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
