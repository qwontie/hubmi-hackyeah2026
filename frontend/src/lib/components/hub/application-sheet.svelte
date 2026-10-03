<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { resolve } from "$app/paths";
  import {
    type AdminApplication,
    type AdminIdeaDetail,
    getApplication,
    getIdea,
    listIdeaMessages,
    type Message,
    replyToIdea,
    setApplicationStatus,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import Stamp from "$lib/components/hub/stamp.svelte";
  import ThreadReply from "$lib/components/hub/thread-reply.svelte";
  import { nbsp, registerNumber } from "$lib/format";
  import { applicationLabel, reviewStatuses } from "$lib/grants";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  let {
    id,
    backHref,
    onchanged,
  }: {
    id: string;
    backHref: string;
    onchanged: (application: AdminApplication) => void;
  } = $props();

  let detail = $state<AdminApplication | null>(null);
  let messages = $state<Message[]>([]);
  let idea = $state<AdminIdeaDetail | null>(null);
  let loadError = $state<Error | null>(null);
  let controller: AbortController | null = null;

  async function load(target: string) {
    controller?.abort();
    controller = new AbortController();
    loadError = null;
    try {
      const next = await getApplication(target, controller.signal);
      if (target !== id) {
        return;
      }
      detail = next;
      if (next.idea) {
        const ideaId = next.idea.id;
        const [thread, full] = await Promise.all([
          listIdeaMessages(ideaId).catch(() => []),
          getIdea(ideaId).catch(() => null),
        ]);
        messages = thread;
        idea = full;
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
      idea = null;
      load(target);
    });
  });

  const offs = [
    live.on("application.updated", (data) => {
      if ((data as { id: string }).id === id) {
        load(id);
      }
    }),
    live.on("application.submitted", (data) => {
      if ((data as { id: string }).id === id) {
        load(id);
      }
    }),
    live.on("message.created", (data) => {
      const m = data as Message;
      if (detail?.idea && m.idea_id === detail.idea.id) {
        messages = [...messages.filter((x) => x.id !== m.id), m];
      }
    }),
  ];

  onDestroy(() => {
    controller?.abort();
    for (const off of offs) {
      off();
    }
  });

  async function change(
    status: "in_review" | "accepted" | "rejected",
    event: MouseEvent
  ) {
    if (!detail || detail.status === status) {
      return;
    }
    const button = event.currentTarget as HTMLElement;
    const before = detail.status;
    detail.status = status;
    try {
      detail = await setApplicationStatus(detail.id, status);
      onchanged(detail);
      showTip(button, "Zapisano");
    } catch (e) {
      if (detail) {
        detail.status = before;
      }
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
    }
  }

  async function reply(body: string) {
    if (!detail?.idea) {
      throw new Error("Ten wniosek nie ma pomysłu, do którego można pisać.");
    }
    const message = await replyToIdea(detail.idea.id, body);
    messages = [...messages.filter((m) => m.id !== message.id), message];
    return message;
  }

  const filled = $derived(
    detail ? detail.sections.filter((s) => s.text.trim()).length : 0
  );
</script>

<article aria-labelledby="application-title" class="sheet">
  {#if detail}
    <div class="grid max-w-[700px] gap-[22px]">
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
        Wnioski
      </a>
      <header
        class="flex items-start justify-between gap-4 max-[899px]:flex-col-reverse"
      >
        <div class="min-w-0">
          <h2
            class="font-semibold text-[22px] tracking-tight"
            id="application-title"
          >
            Wniosek nr {registerNumber(detail.number)}
          </h2>
          <p class="mt-1.5 text-[13px] text-hm-ink-soft">
            {#if detail.idea}
              <a
                class="link"
                href={resolve("/ideas/[[id]]", { id: detail.idea.id })}
                >Pomysł nr {registerNumber(detail.idea.number)}</a
              >
              ·
              {detail.idea_contact ? "autor podał e-mail" : "autor bez e-maila"}
            {:else}
              Wniosek bez pomysłu z&nbsp;Kreatora ·
              {detail.contact_email ? `autor: ${detail.contact_email}` : "autor bez e-maila"}
            {/if}
            · {filled} z&nbsp;{detail.sections.length}
            sekcji
          </p>
          {#if detail.idea}
            <p class="mt-2 text-balance font-semibold text-base">
              {nbsp(detail.idea.title)}
            </p>
          {/if}
        </div>
        {#if detail.submitted_at}
          {#key detail.id}
            <Stamp
              at={detail.submitted_at}
              number={detail.number}
              prefix="WN"
            />
          {/key}
        {/if}
      </header>

      <div class="flex flex-wrap items-center gap-3">
        {#if detail.status === "draft"}
          <p class="text-[13px] text-hm-ink-soft">
            Wersja robocza: autor jeszcze nie złożył wniosku.
          </p>
        {:else}
          <fieldset class="seg">
            <legend class="sr-only">Stan wniosku</legend>
            {#each reviewStatuses as s (s.id)}
              <button
                aria-pressed={detail.status === s.id}
                onclick={(event) => change(s.id, event)}
                type="button"
              >
                {s.label}
              </button>
            {/each}
          </fieldset>
          {#if detail.status === "submitted"}
            <span class="text-[13px] text-hm-ink-soft"
              >{applicationLabel.submitted}, czeka na ocenę</span
            >
          {/if}
        {/if}
        <a class="ghost cladd-clickable ml-auto" download href={detail.pdf_url}>
          <span class="flex items-center gap-2">
            <svg
              aria-hidden="true"
              fill="none"
              height="16"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.75"
              viewBox="0 0 24 24"
              width="16"
            >
              <path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14" />
            </svg>
            Pobierz PDF
          </span>
        </a>
      </div>

      {#if idea}
        <section aria-labelledby="idea-h" class="idea">
          <h3
            class="flex items-baseline gap-2 font-semibold text-[13px]"
            id="idea-h"
          >
            Pomysł autora
            <a
              class="link font-normal"
              href={resolve("/ideas/[[id]]", { id: idea.id })}
              >cała karta pomysłu</a
            >
          </h3>
          <p class="body">{nbsp(idea.essence)}</p>
          {#if idea.for_whom}
            <p class="text-hm-ink-soft text-xs">Dla kogo</p>
            <p class="body">{nbsp(idea.for_whom)}</p>
          {/if}
        </section>
      {/if}

      <ol class="sections">
        {#each detail.sections as s, i (s.key)}
          <li>
            <h3 class="flex items-baseline gap-2 font-semibold text-[13px]">
              <span class="mono-num text-hm-stamp">{i + 1}</span>
              <span>{s.label}</span>
              {#if !s.required}
                <span class="font-normal text-hm-ink-soft">nieobowiązkowa</span>
              {/if}
            </h3>
            {#if s.text.trim()}
              <p class="body">{nbsp(s.text)}</p>
            {:else}
              <p class="text-[13px] text-hm-ink-soft">Pusta.</p>
            {/if}
            {#if s.source === "ai" || s.missing.length > 0}
              <p class="text-hm-ink-soft text-xs">
                {s.source === "ai" ? "Szkic AI, autor go nie poprawiał." : ""}
                {s.missing.length > 0 ? `Brakuje: ${s.missing.join("; ")}.` : ""}
              </p>
            {/if}
          </li>
        {/each}
      </ol>

      {#if detail.idea}
        <section aria-label="Rozmowa z autorem pomysłu">
          <ThreadReply canEmail={detail.idea_contact} {messages} send={reply} />
        </section>
      {:else}
        <p class="text-[13px] text-hm-ink-soft">
          Ten wniosek złożono bez pomysłu z&nbsp;Kreatora.
          {detail.contact_email ? `Autor podał adres ${detail.contact_email}; wysyłka z HubMi do takich wniosków jest w przygotowaniu.` : "Autor nie zostawił adresu."}
        </p>
      {/if}
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
    overscroll-behavior: contain;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: var(--hm-raised);
  }

  .back {
    display: none;
  }

  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-decoration-color: color-mix(
      in oklab,
      var(--hm-stamp) 40%,
      transparent
    );
    text-underline-offset: 3px;
  }

  .idea {
    display: grid;
    gap: 6px;
    padding: 12px 14px;
    background: var(--hm-sunk);
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .seg {
    display: inline-flex;
    gap: 2px;
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
    transition:
      background-color 150ms ease,
      color 150ms ease;
  }

  .seg button:hover {
    color: var(--hm-ink);
  }

  .seg button[aria-pressed="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.6),
      transparent
    );
    box-shadow: var(--shadow-cladd-outline);
  }

  .ghost {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-ink);
    white-space: nowrap;
    background: var(--hm-paper);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-outline);
    transition: background-color 150ms ease;
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  .sections {
    padding: 0;
    margin: 0;
    list-style: none;
    border-top: 1px solid var(--hm-rule);
  }

  .sections li {
    display: grid;
    gap: 6px;
    padding: 14px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .body {
    max-width: 66ch;
    font-size: 15px;
    line-height: 1.55;
    text-wrap: pretty;
    white-space: pre-line;
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
      border-radius: 10px;
    }

    .seg button,
    .ghost {
      height: 44px;
    }

    .ghost {
      margin-left: 0;
    }
  }
</style>
