import {
  type AdminCluster,
  type AdminNeed,
  listClusters,
  listNeeds,
  type NeedCounts,
  needCounts,
} from "$lib/api/admin";
import { live } from "$lib/live/stream.svelte";

const SEEN_KEY = "hubmi.seen";
const SEEN_LIMIT = 2000;

function readSeen(): Set<string> {
  try {
    const raw = localStorage.getItem(SEEN_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

function persist(seen: Set<string>): boolean {
  try {
    localStorage.setItem(
      SEEN_KEY,
      JSON.stringify([...seen].slice(-SEEN_LIMIT))
    );
    return true;
  } catch {
    return false;
  }
}

class Inbox {
  needs = $state<AdminNeed[]>([]);
  clusters = $state<AdminCluster[]>([]);
  counts = $state<NeedCounts | null>(null);
  total = $state(0);
  needsError = $state<Error | null>(null);
  clustersError = $state<Error | null>(null);
  loaded = $state(false);
  arrived = $state<Set<string>>(new Set());
  seen = $state<Set<string>>(readSeen());
  #started: boolean = Boolean(false);

  start() {
    if (this.#started) {
      return;
    }
    this.#started = true;
    live.start();
    live.on("need.created", (data) => {
      this.#upsert(data as AdminNeed, true);
      this.#recount();
    });
    live.on("need.updated", (data) => {
      this.#upsert(data as AdminNeed, false);
      this.#recount();
    });
    live.on("message.created", () => this.#recount());
    live.on("cluster.updated", (data) =>
      this.#upsertCluster(data as AdminCluster)
    );
    live.on("cluster.deleted", (data) => {
      const { id } = data as { id: string };
      this.clusters = this.clusters.filter((c) => c.id !== id);
    });
    live.onReconnect(() => this.refresh());
    this.refresh();
  }

  async refresh() {
    await Promise.all([
      this.#loadNeeds(),
      this.#loadClusters(),
      this.#loadCounts(),
    ]);
    this.loaded = true;
  }

  #recountTimer: ReturnType<typeof setTimeout> | null = null;

  #recount() {
    if (this.#recountTimer) {
      clearTimeout(this.#recountTimer);
    }
    this.#recountTimer = setTimeout(() => {
      this.#recountTimer = null;
      this.#loadCounts();
    }, 400);
  }

  async #loadCounts() {
    try {
      this.counts = await needCounts();
    } catch {
      this.counts = this.counts ?? null;
    }
  }

  async #loadNeeds() {
    try {
      const page = await listNeeds({});
      this.needs = page.items;
      this.total = page.total;
      this.needsError = null;
    } catch (e) {
      this.needsError = e instanceof Error ? e : new Error(String(e));
    }
  }

  async #loadClusters() {
    try {
      const page = await listClusters();
      this.clusters = page.items;
      this.clustersError = null;
    } catch (e) {
      this.clustersError = e instanceof Error ? e : new Error(String(e));
    }
  }

  #upsert(need: AdminNeed, fresh: boolean) {
    const index = this.needs.findIndex((n) => n.id === need.id);
    if (need.status === "junk") {
      if (index !== -1) {
        this.needs = this.needs.filter((n) => n.id !== need.id);
        this.total = Math.max(0, this.total - 1);
      }
      return;
    }
    if (index === -1) {
      this.needs = [need, ...this.needs];
      this.total += 1;
      if (fresh) {
        this.arrived = new Set([...this.arrived, need.id]);
        setTimeout(() => {
          const next = new Set(this.arrived);
          next.delete(need.id);
          this.arrived = next;
        }, 1200);
      }
    } else {
      this.needs[index] = { ...this.needs[index], ...need };
    }
  }

  #upsertCluster(cluster: AdminCluster) {
    const index = this.clusters.findIndex((c) => c.id === cluster.id);
    if (index === -1) {
      this.clusters = [...this.clusters, cluster];
    } else {
      this.clusters[index] = { ...this.clusters[index], ...cluster };
    }
  }

  patch(need: Partial<AdminNeed> & { id: string }) {
    const index = this.needs.findIndex((n) => n.id === need.id);
    if (index === -1) {
      if (need.status && need.status !== "junk" && "text" in need) {
        this.#upsert(need as AdminNeed, false);
      }
    } else if (need.status === "junk") {
      this.needs = this.needs.filter((n) => n.id !== need.id);
      this.total = Math.max(0, this.total - 1);
    } else {
      this.needs[index] = { ...this.needs[index], ...need };
    }
    this.#recount();
  }

  markSeen(id: string) {
    if (this.seen.has(id)) {
      return;
    }
    const next = new Set(this.seen);
    next.add(id);
    this.seen = next;
    persist(next);
  }

  unopened(need: AdminNeed): boolean {
    return need.status === "new" && !this.seen.has(need.id);
  }

  get newCount(): number {
    return (
      this.counts?.waiting ??
      this.needs.filter((n) => n.status === "new").length
    );
  }

  get answeredCount(): number {
    return (
      this.counts?.answered ??
      this.needs.filter((n) => n.status === "answered").length
    );
  }

  get totalCount(): number {
    return this.counts?.total ?? Math.max(this.total, this.needs.length);
  }
}

export const inbox = new Inbox();
