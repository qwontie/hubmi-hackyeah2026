import { listPowiats } from "$lib/api/admin";

class Powiats {
  names = $state(new Map<string, string>());
  #loading: boolean = Boolean(false);

  load() {
    if (this.#loading || this.names.size > 0) {
      return;
    }
    this.#loading = true;
    listPowiats()
      .then((items) => {
        this.names = new Map(items.map((p) => [p.slug, p.name]));
      })
      .catch(() => {
        this.#loading = false;
      });
  }
}

export const powiats = new Powiats();
