import type { Message } from "$lib/api/admin";

export function messageAuthor(m: Message): string {
  if (m.direction === "from_author") {
    return "Autor";
  }
  if (m.expert) {
    return `Ekspert · ${m.expert.display_name}${m.expert.expertise ? `, ${m.expert.expertise}` : ""}`;
  }
  return `ROPS${m.admin ? ` · ${m.admin.login}` : ""}`;
}
