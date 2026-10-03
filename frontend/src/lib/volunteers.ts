import type { VolunteerMessage, VolunteerStatus } from "$lib/api/admin";

export const volunteerStatuses: { id: VolunteerStatus; label: string }[] = [
  { id: "new", label: "Nowe" },
  { id: "accepted", label: "Przyjęte" },
  { id: "reported", label: "Raport przesłany" },
  { id: "closed", label: "Zamknięte" },
  { id: "rejected", label: "Odrzucone" },
];

export const volunteerLabel: Record<VolunteerStatus, string> = {
  accepted: "Przyjęte",
  closed: "Zamknięte",
  new: "Nowe",
  rejected: "Odrzucone",
  reported: "Raport przesłany",
};

export const recommendLabel = {
  after_changes: "Tak, po zmianach",
  no: "Nie",
  yes: "Tak",
} as const;

export const messageKind: Record<VolunteerMessage["kind"], string> = {
  accept: "Przyjęcie",
  message: "Wiadomość",
  reject: "Odmowa",
};

export const deliveryWord: Record<VolunteerMessage["delivery_status"], string> =
  {
    failed: "e-mail nie dotarł",
    pending: "wysyłanie…",
    sent: "wysłano e-mailem",
    skipped: "bez e-maila, wysyłka wyłączona",
  };
