import { type Me, me } from "$lib/api/auth";
import { ApiError } from "$lib/api/client";

class Session {
  me = $state<Me | null>(null);
  loaded = $state(false);
  error = $state<Error | null>(null);

  async load() {
    this.error = null;
    try {
      this.me = await me();
    } catch (e) {
      this.me = null;
      if (!(e instanceof ApiError && e.status === 401)) {
        this.error = e instanceof Error ? e : new Error(String(e));
      }
    } finally {
      this.loaded = true;
    }
  }

  set(value: Me | null) {
    this.me = value;
    this.loaded = true;
    this.error = null;
  }
}

export const session = new Session();
