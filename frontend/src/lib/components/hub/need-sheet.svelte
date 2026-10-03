<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import {
    type AdminNeed,
    type AdminNeedDetail,
    getNeed,
    type Message,
    markNeedRead,
    type NeedStatus,
    replyToNeed,
    setNeedStatus,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import ExpertPanel from "$lib/components/hub/expert-panel.svelte";
  import ReplyBuilder from "$lib/components/hub/reply-builder.svelte";
  import Stamp from "$lib/components/hub/stamp.svelte";
  import {
    nbsp,
    powiatName,
    registerNumber,
    statusLabel,
    when,
  } from "$lib/format";
  import { inbox } from "$lib/live/inbox.svelte";
  import { powiats } from "$lib/live/powiats.svelte";
  import { live } from "$lib/live/stream.svelte";
  import { messageAuthor } from "$lib/message";
  import { showTip } from "$lib/tip";

  let {
    id,
    folder,
    backHref,
  }: { id: string; folder: string; backHref: string } = $props();

  let detail = $state<AdminNeedDetail | null>(null);
  let loadError = $state<Error | null>(null);
  let body = $state("");
  let sending = $state(false);
  let sentStamp = $state<"sent" | "failed" | "saved" | null>(null);
  let replyField = $state<HTMLTextAreaElement | null>(null);
  let controller: AbortController | null = null;

  const listed = $derived(inbox.needs.find((n) => n.id === id) ?? null);
  const need = $derived<AdminNeed | null>(detail ?? listed);
  const statuses: NeedStatus[] = ["new", "answered", "closed"];

  async function load(target: string) {
    controller?.abort();
    controller = new AbortController();
    loadError = null;
    try {
      const next = await getNeed(target, controller.signal);
      if (target === id) {
        detail = next;
        if ((next.unread ?? 0) > 0) {
          markNeedRead(target).catch(() => undefined);
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
      body = "";
      sentStamp = null;
      inbox.markSeen(target);
      load(target);
    });
  });

  const offs = [
    live.on("need.updated", (data) => {
      const next = data as AdminNeed;
      if (detail && next.id === detail.id) {
        detail = { ...detail, ...next };
      }
    }),
    live.on("message.created", (data) => upsertMessage(data as Message)),
    live.on("message.updated", (data) => {
      const message = data as Message;
      upsertMessage(message);
      if (
        message.need_id === id &&
        message.direction === "to_author" &&
        sentStamp
      ) {
        if (message.delivery_status === "failed") {
          sentStamp = "failed";
        } else if (message.delivery_status === "skipped") {
          sentStamp = "saved";
        }
      }
    }),
  ];

  onDestroy(() => {
    controller?.abort();
    for (const off of offs) {
      off();
    }
  });

  function upsertMessage(message: Message) {
    if (!detail || message.need_id !== detail.id) {
      return;
    }
    const index = detail.messages.findIndex((m) => m.id === message.id);
    detail.messages =
      index === -1
        ? [...detail.messages, message]
        : detail.messages.map((m) => (m.id === message.id ? message : m));
  }

  async function changeStatus(status: NeedStatus, event: MouseEvent) {
    if (!need || need.status === status) {
      return;
    }
    const button = event.currentTarget as HTMLElement;
    const before = need.status;
    inbox.patch({ id: need.id, status });
    if (detail) {
      detail.status = status;
    }
    try {
      const saved = await setNeedStatus(need.id, status);
      inbox.patch(saved);
      showTip(button, "Zapisano");
    } catch (e) {
      inbox.patch({ id: need.id, status: before });
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

  async function send(event?: Event) {
    event?.preventDefault();
    const button = document.getElementById("send-reply");
    const text = body.trim();
    if (!(need && text) || sending) {
      replyField?.focus();
      showTip(button, "Najpierw napisz odpowiedź", "bad");
      return;
    }
    sending = true;
    sentStamp = null;
    try {
      const message = await replyToNeed(need.id, text);
      upsertMessage(message);
      body = "";
      inbox.patch({ id: need.id, status: "answered" });
      if (detail) {
        detail.status = "answered";
      }
      sentStamp = stampFor(message);
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Brak połączenia z serwerem.",
        "bad"
      );
    } finally {
      sending = false;
    }
  }

  function stampFor(message: Message): "sent" | "failed" | "saved" {
    if (message.delivery_status === "failed") {
      return "failed";
    }
    if (message.delivery_status === "skipped") {
      return "saved";
    }
    return "sent";
  }

  const stampWords = {
    failed: "Nie wysłano",
    saved: "Zapisano",
    sent: "Wysłano",
  };

  function keydown(event: KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      send(event);
    }
  }

  export function focusReply() {
    replyField?.focus();
  }

  export function pressStatus(status: NeedStatus) {
    const button = document.querySelector<HTMLButtonElement>(
      `[data-status="${status}"]`
    );
    button?.click();
  }

  const deliveryWord = (m: Message) => {
    if (m.direction === "from_author") {
      return "";
    }
    switch (m.delivery_status) {
      case "sent":
        return "wysłano e-mailem";
      case "pending":
        return "wysyłanie…";
      case "failed":
        return "e-mail nie dotarł";
      case "skipped":
        return "bez e-maila, wysyłka wyłączona";
      default:
        return "widoczne w aplikacji";
    }
  };
  const meta = $derived.by(() => {
    if (!need) {
      return [] as string[];
    }
    const parts: string[] = [];
    const p = powiatName(need.powiat, powiats.names);
    if (p) {
      parts.push(
        p.startsWith("powiat") || p.startsWith("m.") ? p : `powiat ${p}`
      );
    }
    const contact =
      detail?.can_email ?? need.has_contact ?? Boolean(need.contact_email);
    parts.push(contact ? "autor podał e-mail" : "autor bez e-maila");
    if (need.cluster && need.cluster.id !== folder) {
      parts.push(
        inbox.clusters.find((c) => c.id === need.cluster?.id)?.title ??
          need.cluster.title
      );
    }
    if (need.nothing_fits) {
      parts.push("nic nie pasowało");
    }
    return parts;
  });
</script>

<article aria-labelledby="need-title" class="sheet">
  {#if need}
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
        Dziennik
      </a>
      <header
        class="flex items-start justify-between gap-4 max-[899px]:flex-col-reverse"
      >
        <div class="min-w-0">
          <h2 class="font-semibold text-[22px] tracking-tight" id="need-title">
            Potrzeba {need.number ? `nr ${registerNumber(need.number)}` : ""}
          </h2>
          <p class="mt-1.5 text-[13px] text-hm-ink-soft">{meta.join(" · ")}</p>
        </div>
        {#key need.id}
          <Stamp at={need.created_at} number={need.number} />
        {/key}
      </header>

      <p class="reading">{nbsp(need.text)}</p>

      <fieldset class="seg">
        <legend class="sr-only">Stan potrzeby</legend>
        {#each statuses as s (s)}
          <button
            aria-pressed={need.status === s}
            data-status={s}
            onclick={(event) => changeStatus(s, event)}
            type="button"
          >
            {statusLabel[s]}
          </button>
        {/each}
      </fieldset>

      {#if loadError}
        <ErrorState class="py-4" error={loadError} retry={() => load(id)} />
      {:else if detail}
        {#if detail.match_details.length > 0}
          <section aria-labelledby="matches-h">
            <h3 class="mb-1.5 font-semibold text-[13px]" id="matches-h">
              Co już działa w&nbsp;Małopolsce
            </h3>
            <ol class="matches">
              {#each detail.match_details as m (m.innovation.slug)}
                <li>
                  <span class="mono-num font-semibold text-hm-stamp text-[13px]"
                    >{m.rank}</span
                  >
                  <span class="font-semibold text-sm"
                    >{m.innovation.title}</span
                  >
                  <span class="text-right text-hm-ink-soft text-xs tabular"
                    >{Math.round(m.score * 100)}%</span
                  >
                  <span class="reason">{m.reason}</span>
                </li>
              {/each}
            </ol>
          </section>
        {:else}
          <p class="text-[13px] text-hm-ink-soft">
            Żadna innowacja z&nbsp;biblioteki nie pasowała do tego opisu.
          </p>
        {/if}

        <ExpertPanel id={detail.id} kind="needs" />

        {#if detail.messages.length > 0}
          <section aria-labelledby="thread-h">
            <h3 class="mb-1.5 font-semibold text-[13px]" id="thread-h">
              Rozmowa
            </h3>
            <ol class="thread">
              {#each detail.messages as m (m.id)}
                <li>
                  <span class="text-hm-ink-soft text-xs">
                    <b class="font-semibold text-hm-ink">{messageAuthor(m)}</b>
                    ·
                    {when(m.sent_at)}{deliveryWord(m) ? ` · ${deliveryWord(m)}` : ""}
                  </span>
                  <p class="whitespace-pre-line text-sm">{m.body}</p>
                </li>
              {/each}
            </ol>
          </section>
        {/if}

        <form class="grid gap-2" onsubmit={send}>
          <h3 class="font-semibold text-[13px]">
            <label for="reply">Odpowiedź do autora</label>
          </h3>
          <ReplyBuilder
            auto={detail.status === "new" &&
              !detail.messages.some((m) => m.direction === "to_author")}
            needId={detail.id}
            bind:body
          />
          <div class="reply">
            <textarea
              id="reply"
              maxlength="5000"
              onkeydown={keydown}
              placeholder={detail.can_email
                ? "Wiadomość pójdzie e-mailem na adres podany przez autora."
                : "Autor nie podał e-maila. Odpowiedź zobaczy w aplikacji, w swoim zgłoszeniu."}
              rows="4"
              bind:this={replyField}
              bind:value={body}
            ></textarea>
            <div
              class="flex items-center justify-between gap-2.5 py-1.5 pr-1.5 pl-3.5 text-hm-ink-soft text-xs"
            >
              <span class="max-[899px]:hidden"
                ><kbd>Ctrl</kbd> <kbd>Enter</kbd> wyślij</span
              >
              <span class="relative ml-auto flex items-center gap-3">
                {#if sentStamp}
                  <span
                    class={["sent", sentStamp === "failed" && "failed", sentStamp === "saved" && "saved", "hm-land stamp-word"]}
                    role="status"
                  >
                    {stampWords[sentStamp]}
                  </span>
                {/if}
                <button
                  class="primary cladd-clickable"
                  disabled={sending}
                  id="send-reply"
                  type="submit"
                >
                  <span class="flex items-center gap-2">
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
                      <path d="M5 12h14" />
                      <path d="m12 5 7 7-7 7" />
                    </svg>
                    {sending ? "Wysyłanie…" : "Wyślij odpowiedź"}
                  </span>
                </button>
              </span>
            </div>
          </div>
        </form>
      {:else}
        <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
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
    letter-spacing: -0.005em;
    text-wrap: pretty;
    white-space: pre-line;
  }

  .seg {
    display: inline-flex;
    gap: 2px;
    justify-self: start;
    padding: 3px;
    background: var(--hm-sunk);
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

  .matches,
  .thread {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .matches li {
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr) auto;
    gap: 2px 10px;
    padding: 10px 0;
    border-bottom: 1px dashed var(--hm-rule);
  }

  .matches li:last-child {
    border-bottom: 0;
  }

  .matches .reason {
    grid-column: 2 / 4;
    font-size: 13px;
    line-height: 1.45;
    color: var(--hm-ink-soft);
  }

  .thread li {
    display: grid;
    gap: 3px;
    padding: 10px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .thread li:last-child {
    border-bottom: 0;
  }

  .reply {
    background: var(--hm-sunk);
    border-radius: 14px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .reply:focus-within {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .reply textarea {
    display: block;
    width: 100%;
    min-height: 100px;
    resize: vertical;
    border: 0;
    background: none;
    outline: none;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.5;
    field-sizing: content;
  }

  .reply textarea::placeholder {
    color: var(--hm-ink-soft);
  }

  kbd {
    padding: 3px 5px;
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--hm-board);
    border-radius: 5px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .primary {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-on-stamp);
    white-space: nowrap;
    background-color: var(--hm-stamp);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.16),
      transparent
    );
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-outline-fill);
    transition: background-color 150ms ease;
  }

  .primary:hover {
    background-color: var(--hm-stamp-press);
  }

  .primary:disabled {
    opacity: 0.6;
  }

  .sent {
    padding: 2px 8px;
    color: var(--hm-ok);
    border: 2px solid currentColor;
    border-radius: 6px;
    rotate: -4deg;
  }

  .sent.failed {
    color: var(--hm-bad);
  }

  .sent.saved {
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
      border-radius: 10px;
    }

    .reading {
      font-size: 16px;
    }

    .primary {
      height: 44px;
    }
  }
</style>
