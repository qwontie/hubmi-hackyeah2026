<script lang="ts">
  import { untrack } from "svelte";
  import {
    type ReplyFragment,
    type ReplySuggestions,
    replySuggestions,
    storedReplySuggestions,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { registerNumber } from "$lib/format";

  let { needId, body = $bindable("") }: { needId: string; body: string } =
    $props();

  interface Slip {
    hint: string;
    id: string;
    kind: ReplyFragment["kind"] | "earlier";
    label: string;
    text: string;
  }

  const rank: Record<Slip["kind"], number> = {
    closing: 4,
    earlier: 2,
    innovation: 1,
    next_step: 3,
    opening: 0,
  };

  let data = $state<ReplySuggestions | null>(null);
  let busy = $state(false);
  let slow = $state(false);
  let failure = $state<string | null>(null);
  let controller: AbortController | null = null;

  async function peek(target: string) {
    controller?.abort();
    controller = new AbortController();
    try {
      const stored = await storedReplySuggestions(target, controller.signal);
      if (target === needId && stored) {
        data = stored;
      }
    } catch {
      data = null;
    }
  }

  async function generate(target: string, refresh: boolean) {
    controller?.abort();
    controller = new AbortController();
    busy = true;
    failure = null;
    const timer = setTimeout(() => {
      slow = true;
    }, 300);
    try {
      const next = await replySuggestions(target, refresh, controller.signal);
      if (target === needId) {
        data = next;
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return;
      }
      if (target === needId) {
        failure = messageOf(
          e,
          "Podpowiedzi są teraz niedostępne. Napisz odpowiedź samodzielnie.",
          "Brak połączenia z serwerem."
        );
      }
    } finally {
      clearTimeout(timer);
      if (target === needId) {
        busy = false;
        slow = false;
      }
    }
  }

  $effect(() => {
    const target = needId;
    untrack(() => {
      controller?.abort();
      data = null;
      failure = null;
      busy = false;
      slow = false;
      peek(target);
    });
  });

  const slips = $derived<Slip[]>(
    (data?.fragments ?? []).map((f) => ({
      hint: f.text,
      id: f.id,
      kind: f.kind,
      label: f.label,
      text: f.text.trim(),
    }))
  );

  const earlier = $derived(
    (data?.earlier_answers ?? []).map((a, i) => ({
      answer: a,
      slip: {
        hint: a.body,
        id: `earlier:${i}`,
        kind: "earlier" as const,
        label: a.need_number
          ? `Odpowiedź do nr ${registerNumber(a.need_number)}`
          : "Wcześniejsza odpowiedź",
        text: a.body.trim(),
      },
    }))
  );

  const allSlips = $derived([...slips, ...earlier.map((e) => e.slip)]);
  const used = (slip: Slip) => slip.text !== "" && body.includes(slip.text);

  function tidy(text: string) {
    return text.replace(/\n{3,}/g, "\n\n").replace(/^\s+|\s+$/g, "");
  }

  function toggle(slip: Slip) {
    if (used(slip)) {
      body = tidy(body.replace(slip.text, ""));
      return;
    }
    const [after] = allSlips
      .filter(
        (s) => s.id !== slip.id && used(s) && rank[s.kind] > rank[slip.kind]
      )
      .map((s) => body.indexOf(s.text))
      .filter((i) => i >= 0)
      .sort((a, b) => a - b);
    if (after === undefined) {
      body = tidy(`${body.trimEnd()}\n\n${slip.text}`);
    } else {
      body = tidy(
        `${body.slice(0, after).trimEnd()}\n\n${slip.text}\n\n${body.slice(after)}`
      );
    }
  }

  function messageOf(e: unknown, unavailable: string, offline: string) {
    if (!(e instanceof ApiError)) {
      return offline;
    }
    return e.status === 503 ? unavailable : e.message;
  }

  const pct = (v: number) => `${Math.round(v * 100)}%`;
</script>

<div class="builder">
  {#if data && (slips.length > 0 || earlier.length > 0)}
    {#if slips.length > 0}
      <fieldset class="slips">
        <legend class="label">
          Podpowiedzi do wstawienia
          <span class="ai">AI</span>
        </legend>
        {#each slips as slip (slip.id)}
          <button
            aria-pressed={used(slip)}
            class={["slip", slip.kind === "innovation" && "inn"]}
            onclick={() => toggle(slip)}
            title={slip.hint}
            type="button"
          >
            <svg
              aria-hidden="true"
              fill="none"
              height="14"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              viewBox="0 0 24 24"
              width="14"
            >
              {#if used(slip)}
                <path d="m5 12.5 4.5 4.5L19 7.5" />
              {:else}
                <path d="M12 5v14M5 12h14" />
              {/if}
            </svg>
            <span class="clamp-line">{slip.label}</span>
          </button>
        {/each}
        <button
          class="again"
          disabled={busy}
          onclick={() => generate(needId, true)}
          type="button"
        >
          {busy ? "Układanie…" : "Napisz od nowa"}
        </button>
      </fieldset>
    {/if}
    {#if earlier.length > 0}
      <details class="earlier">
        <summary>
          Podobne odpowiedzi ROPS
          <span class="tabular">{earlier.length}</span>
        </summary>
        <ol>
          {#each earlier as e (e.slip.id)}
            <li>
              <span class="text-hm-ink-soft text-xs">
                <b class="font-semibold text-hm-ink">{e.slip.label}</b>
                · {pct(e.answer.similarity)}
                podobieństwa{e.answer.demo ? " · dane pokazowe" : ""}
              </span>
              <p class="excerpt">{e.answer.need_excerpt}</p>
              <p class="answer">{e.answer.body}</p>
              <button
                aria-pressed={used(e.slip)}
                class="slip"
                onclick={() => toggle(e.slip)}
                type="button"
              >
                <svg
                  aria-hidden="true"
                  fill="none"
                  height="14"
                  stroke="currentColor"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  viewBox="0 0 24 24"
                  width="14"
                >
                  {#if used(e.slip)}
                    <path d="m5 12.5 4.5 4.5L19 7.5" />
                  {:else}
                    <path d="M12 5v14M5 12h14" />
                  {/if}
                </svg>
                <span>{used(e.slip) ? "Wstawiono" : "Wstaw tę odpowiedź"}</span>
              </button>
            </li>
          {/each}
        </ol>
      </details>
    {/if}
  {:else if failure}
    <p class="note" role="status">
      {failure}
      <button
        class="link"
        onclick={() => generate(needId, false)}
        type="button"
      >
        Spróbuj ponownie
      </button>
    </p>
  {:else if busy}
    <p aria-live="polite" class="note">
      {slow ? "Układanie podpowiedzi…" : ""}
    </p>
  {:else}
    <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <button
        class="ask cladd-clickable"
        onclick={() => generate(needId, false)}
        type="button"
      >
        <span class="flex items-center gap-2">
          <svg
            aria-hidden="true"
            fill="none"
            height="15"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.75"
            viewBox="0 0 24 24"
            width="15"
          >
            <path d="M4 6h10M4 12h16M4 18h7" />
          </svg>
          Podpowiedz odpowiedź
          <span class="ai">AI</span>
        </span>
      </button>
      <span class="note">
        Model ułoży fragmenty z&nbsp;treści zgłoszenia. Nic nie wyśle się samo.
      </span>
    </div>
  {/if}
</div>

<style>
  .builder {
    display: grid;
    gap: 8px;
    min-height: 36px;
  }

  .slips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    min-width: 0;
    padding: 0;
    margin: 0;
    border: 0;
  }

  .label {
    float: left;
    display: flex;
    gap: 6px;
    align-items: center;
    width: 100%;
    margin-bottom: 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .ai {
    display: inline-flex;
    align-items: center;
    height: 16px;
    padding: 0 5px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
    color: var(--hm-ink-soft);
    letter-spacing: 0.08em;
    border: 1px solid currentColor;
    border-radius: 4px;
  }

  .slip {
    position: relative;
    display: inline-flex;
    gap: 6px;
    align-items: center;
    max-width: 260px;
    height: 32px;
    padding: 0 11px 0 9px;
    font-size: 13px;
    font-weight: 560;
    color: var(--hm-ink);
    background: var(--hm-paper);
    border-radius: 10px;
    box-shadow:
      0 0 0 1px var(--hm-rule),
      0 1px 2px oklch(0.3 0.03 280 / 0.06);
    transition:
      background-color 150ms ease,
      box-shadow 150ms ease,
      translate 150ms ease;
  }

  .slip svg {
    flex: none;
    color: var(--hm-stamp);
  }

  .slip:hover {
    box-shadow:
      0 0 0 1px color-mix(in oklab, var(--hm-stamp) 40%, var(--hm-rule)),
      0 6px 14px -8px oklch(0.3 0.06 280 / 0.35);
    translate: 0 -1px;
  }

  .slip[aria-pressed="true"] {
    background: var(--hm-stamp-wash);
    box-shadow: 0 0 0 1px color-mix(in oklab, var(--hm-stamp) 30%, transparent);
  }

  .slip[aria-pressed="true"]:hover {
    translate: none;
  }

  .slip.inn span {
    font-weight: 500;
  }

  .again,
  .link {
    height: 32px;
    padding: 0 8px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    text-decoration: underline;
    text-decoration-color: var(--hm-rule);
    text-underline-offset: 3px;
    border-radius: 8px;
  }

  .again:hover,
  .link:hover {
    color: var(--hm-stamp);
  }

  .link {
    height: auto;
    padding: 0;
  }

  .note {
    margin: 0;
    font-size: 13px;
    color: var(--hm-ink-soft);
  }

  .ask {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-self: start;
    height: 34px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-ink);
    background: var(--hm-paper);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-outline);
    transition: background-color 150ms ease;
  }

  .ask:hover {
    background: var(--hm-stamp-wash);
  }

  .earlier summary {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    min-height: 32px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    cursor: pointer;
    list-style: none;
    border-radius: 8px;
  }

  .earlier summary::-webkit-details-marker {
    display: none;
  }

  .earlier summary::before {
    width: 6px;
    height: 6px;
    content: "";
    border-right: 1.5px solid currentColor;
    border-bottom: 1.5px solid currentColor;
    rotate: -45deg;
    transition: rotate 150ms ease;
  }

  .earlier[open] summary::before {
    rotate: 45deg;
  }

  .earlier summary:hover {
    color: var(--hm-ink);
  }

  .earlier ol {
    padding: 0;
    margin: 4px 0 0;
    list-style: none;
  }

  .earlier li {
    display: grid;
    gap: 6px;
    padding: 10px 0;
    border-top: 1px dashed var(--hm-rule);
  }

  .excerpt {
    margin: 0;
    font-size: 13px;
    font-style: italic;
    color: var(--hm-ink-soft);
  }

  .answer {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    margin: 0;
    overflow: hidden;
    -webkit-line-clamp: 4;
    line-clamp: 4;
    font-size: 13px;
    white-space: pre-line;
  }

  .earlier .slip {
    justify-self: start;
  }

  @media (max-width: 899px) {
    .slip,
    .again,
    .ask,
    .earlier summary {
      height: 44px;
      min-height: 44px;
    }
  }
</style>
