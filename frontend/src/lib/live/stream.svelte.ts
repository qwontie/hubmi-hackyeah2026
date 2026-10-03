import { api } from "$lib/api/client";

export type LiveState = "connecting" | "open" | "offline";

type Handler = (data: unknown) => void;

const TOPICS = [
  "need.created",
  "need.updated",
  "cluster.updated",
  "cluster.deleted",
  "import.progress",
  "import.finished",
  "innovation.updated",
  "message.created",
  "message.updated",
  "idea.created",
  "idea.updated",
  "feedback.created",
  "test_signup.created",
  "knowledge.import.progress",
  "knowledge.import.finished",
  "material.updated",
  "challenge.updated",
  "assignment.created",
  "assignment.answered",
] as const;

export type Topic = (typeof TOPICS)[number];

class LiveStream {
  state = $state<LiveState>("connecting");
  #source: EventSource | null = null;
  readonly #handlers = new Map<Topic, Set<Handler>>();
  readonly #reconnect = new Set<() => void>();
  #wasOpen: boolean = Boolean(false);
  #offlineTimer: ReturnType<typeof setTimeout> | null = null;

  start() {
    if (this.#source) {
      return;
    }
    const source = new EventSource(api.url("/stream"), {
      withCredentials: true,
    });
    this.#source = source;
    this.state = "connecting";
    source.onopen = () => {
      if (this.#offlineTimer) {
        clearTimeout(this.#offlineTimer);
        this.#offlineTimer = null;
      }
      if (this.#wasOpen) {
        for (const fn of this.#reconnect) {
          fn();
        }
      }
      this.#wasOpen = true;
      this.state = "open";
    };
    source.onerror = () => {
      this.state = "connecting";
      this.#offlineTimer ??= setTimeout(() => {
        if (this.state !== "open") {
          this.state = "offline";
        }
      }, 10_000);
      if (source.readyState === EventSource.CLOSED) {
        this.stop();
        setTimeout(() => this.start(), 5000);
      }
    };
    for (const topic of TOPICS) {
      source.addEventListener(topic, (event) => {
        let data: unknown = null;
        try {
          data = JSON.parse((event as MessageEvent<string>).data);
        } catch {
          return;
        }
        for (const fn of this.#handlers.get(topic) ?? []) {
          fn(data);
        }
      });
    }
  }

  stop() {
    this.#source?.close();
    this.#source = null;
  }

  on(topic: Topic, fn: Handler): () => void {
    const set = this.#handlers.get(topic) ?? new Set<Handler>();
    set.add(fn);
    this.#handlers.set(topic, set);
    return () => set.delete(fn);
  }

  onReconnect(fn: () => void): () => void {
    this.#reconnect.add(fn);
    return () => this.#reconnect.delete(fn);
  }
}

export const live = new LiveStream();
