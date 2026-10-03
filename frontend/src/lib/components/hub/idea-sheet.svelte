<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { resolve } from "$app/paths";
  import {
    type AdminIdea,
    type AdminIdeaDetail,
    getIdea,
    type IdeaOptions,
    type IdeaStatus,
    listIdeaMessages,
    type Message,
    markIdeaRead,
    replyToIdea,
    setIdeaStatus,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import Stamp from "$lib/components/hub/stamp.svelte";
  import ThreadReply from "$lib/components/hub/thread-reply.svelte";
  import { nbsp, powiatName, registerNumber } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  let {
    id,
    options,
    backHref,
    onchange,
  }: {
    id: string;
    options: IdeaOptions | null;
    backHref: string;
    onchange: (idea: AdminIdea) => void;
  } = $props();

  const statuses: { id: IdeaStatus; label: string }[] = [
    { id: "new", label: "Nowy" },
    { id: "in_review", label: "W ocenie" },
    { id: "accepted", label: "Przyjęty" },
    { id: "rejected", label: "Odrzucony" },
  ];

  let detail = $state<AdminIdeaDetail | null>(null);
  let messages = $state<Message[]>([]);
  let loadError = $state<Error | null>(null);
  let controller: AbortController | null = null;

  async function load(target: string) {
    controller?.abort();
    controller = new AbortController();
    loadError = null;
    try {
      const [item, thread] = await Promise.all([
        getIdea(target, controller.signal),
        listIdeaMessages(target).catch(() => [] as Message[]),
      ]);
      if (target === id) {
        detail = item;
        messages = thread;
        if (thread.some((m) => m.direction === "from_author" && !m.read_at)) {
          markIdeaRead(target).catch(() => undefined);
        }
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return;
      }
      loadError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    const target = id;
    untrack(() => {
      detail = null;
      messages = [];
      load(target);
    });
  });

  function upsertMessage(message: Message) {
    if (message.idea_id !== id) {
      return;
    }
    const index = messages.findIndex((m) => m.id === message.id);
    messages =
      index === -1
        ? [...messages, message]
        : messages.map((m) => (m.id === message.id ? message : m));
  }

  const offs = [
    live.on("idea.updated", (data) => {
      const next = data as AdminIdea;
      if (detail && next.id === detail.id) {
        detail = { ...detail, ...next };
      }
    }),
    live.on("message.created", (data) => upsertMessage(data as Message)),
    live.on("message.updated", (data) => upsertMessage(data as Message)),
  ];

  onDestroy(() => {
    controller?.abort();
    for (const off of offs) {
      off();
    }
  });

  async function reply(body: string): Promise<Message> {
    const message = await replyToIdea(id, body);
    upsertMessage({ ...message, idea_id: message.idea_id ?? id });
    return message;
  }

  async function change(status: IdeaStatus, event: MouseEvent) {
    if (!detail || detail.status === status) {
      return;
    }
    const button = event.currentTarget as HTMLElement;
    const before = detail.status;
    detail.status = status;
    try {
      detail = await setIdeaStatus(detail.id, status);
      onchange(detail);
      showTip(
        button,
        status === "accepted"
          ? "Przyjęto, pomysł jest teraz publiczny"
          : "Zapisano"
      );
    } catch (e) {
      detail.status = before;
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
    }
  }

  const stageName = (slug: string) =>
    options?.stages.find((s) => s.slug === slug)?.name ?? slug;
  const canvasRows = $derived(
    (options?.canvas_fields ?? [])
      .map((f) => ({
        label: f.name,
        value: detail?.canvas?.[f.field]?.trim() ?? "",
      }))
      .filter((r) => r.value !== "")
  );
</script>

<article aria-labelledby="idea-title" class="sheet">
  {#if detail}
    <div class="grid max-w-[680px] gap-[22px]">
      <a class="back" href={backHref}>
        <svg
          aria-hidden="true"
          fill="none"
          height="16"
          stroke="currentColor"
          stroke-linecap="round"
          stroke-width="1.75"
          viewBox="0 0 24 24"
          width="16"
        >
          <path d="m15 18-6-6 6-6" />
        </svg>
        Pomysły
      </a>
      <header
        class="flex items-start justify-between gap-4 max-[899px]:flex-col-reverse"
      >
        <div class="min-w-0">
          <h2 class="font-semibold text-[22px] tracking-tight" id="idea-title">
            {nbsp(detail.title)}
          </h2>
          <p class="mt-1.5 text-[13px] text-hm-ink-soft">
            Pomysł nr {registerNumber(detail.number)} ·
            {stageName(detail.stage)}{detail.powiat ? ` · ${powiatName(detail.powiat, powiats.names)}` : ""}
          </p>
        </div>
        {#key detail.id}
          <Stamp at={detail.created_at} number={detail.number} />
        {/key}
      </header>

      <p class="reading">{nbsp(detail.essence)}</p>
      <p class="text-sm">
        <b class="font-semibold">Dla kogo:</b> {detail.for_whom}
      </p>

      <fieldset class="seg">
        <legend class="sr-only">Stan pomysłu</legend>
        {#each statuses as s (s.id)}
          <button
            aria-pressed={detail.status === s.id}
            onclick={(event) => change(s.id, event)}
            type="button"
          >
            {s.label}
          </button>
        {/each}
      </fieldset>

      {#if canvasRows.length > 0}
        <section aria-labelledby="canvas-h">
          <h3 class="mb-1.5 font-semibold text-[13px]" id="canvas-h">
            Kanwa innowacji
          </h3>
          <dl class="canvas">
            {#each canvasRows as row (row.label)}
              <div>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            {/each}
          </dl>
        </section>
      {/if}

      {#if detail.similar_innovations.length > 0}
        <section aria-labelledby="sim-inn-h">
          <h3 class="mb-1.5 font-semibold text-[13px]" id="sim-inn-h">
            Podobne innowacje z&nbsp;biblioteki
          </h3>
          <ul class="list">
            {#each detail.similar_innovations as inn (inn.slug)}
              <li>
                <a href="{resolve('/library')}/{inn.slug}">{inn.title}</a
                ><span class="tabular"
                  >{Math.round(inn.similarity * 100)}%</span
                >
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if detail.similar_ideas.length > 0}
        <section aria-labelledby="sim-idea-h">
          <h3 class="mb-1.5 font-semibold text-[13px]" id="sim-idea-h">
            Podobne pomysły innych osób
          </h3>
          <ul class="list">
            {#each detail.similar_ideas as other (other.id)}
              <li>
                <a href="{resolve('/ideas')}/{other.id}"
                  >nr {registerNumber(other.number)} · {other.title}</a
                ><span class="tabular"
                  >{Math.round(other.similarity * 100)}%</span
                >
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      <ThreadReply
        canEmail={Boolean(detail.contact_email)}
        {messages}
        send={reply}
      />
    </div>
  {:else if loadError}
    <ErrorState error={loadError} retry={() => load(id)} />
  {:else}
    <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
  {/if}
</article>

<style>
  .sheet {
    position: relative;
    min-height: 0;
    padding: 26px 30px 30px;
    overflow: auto;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: var(--hm-raised);
  }

  .back {
    display: none;
  }

  .reading {
    max-width: 62ch;
    font-size: 18px;
    line-height: 1.55;
    text-wrap: pretty;
    white-space: pre-line;
  }

  .seg {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 2px;
    justify-self: start;
    padding: 3px;
    margin: 0;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .seg button {
    position: relative;
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
    border-radius: 9px;
  }

  .seg button:hover {
    color: var(--hm-ink);
  }

  .seg button[aria-pressed="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  .canvas {
    display: grid;
    margin: 0;
  }

  .canvas div {
    display: grid;
    grid-template-columns: 160px minmax(0, 1fr);
    gap: 12px;
    padding: 8px 0;
    font-size: 13px;
    border-bottom: 1px solid var(--hm-rule);
  }

  .canvas div:last-child {
    border-bottom: 0;
  }

  .canvas dt {
    font-weight: 600;
  }

  .canvas dd {
    margin: 0;
    white-space: pre-line;
  }

  .list {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .list li {
    display: flex;
    gap: 12px;
    justify-content: space-between;
    padding: 8px 0;
    font-size: 14px;
    border-bottom: 1px dashed var(--hm-rule);
  }

  .list li:last-child {
    border-bottom: 0;
  }

  .list a {
    font-weight: 600;
  }

  .list a:hover {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .list span {
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  @media (max-width: 899px) {
    .sheet {
      padding: 16px;
      border-radius: 18px;
    }

    .back {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      justify-self: start;
      min-height: 44px;
      padding: 0 10px 0 4px;
      font-size: 14px;
      font-weight: 500;
    }

    .reading {
      font-size: 16px;
    }

    .canvas div {
      grid-template-columns: minmax(0, 1fr);
      gap: 2px;
    }

    .seg button {
      height: 40px;
    }
  }
</style>
