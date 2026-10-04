<script lang="ts">
  import { tick } from "svelte";
  import type { AdminInnovationDetail } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import {
    listPicturePool,
    type PictureFields,
    type PoolPicture,
    usePoolPicture,
  } from "$lib/pictures";
  import { showTip } from "$lib/tip";

  let {
    slug,
    category,
    label,
    onpicked,
  }: {
    slug: string;
    category: string;
    label: string;
    onpicked: (item: AdminInnovationDetail & PictureFields) => void;
  } = $props();

  let dialog = $state<HTMLDialogElement | null>(null);
  let trigger = $state<HTMLButtonElement | null>(null);
  let pool = $state<PoolPicture[] | null>(null);
  let poolError = $state<string | null>(null);
  let shown = $state("all");
  let busy = $state<string | null>(null);

  const categories = $derived([
    ...new Map((pool ?? []).map((p) => [p.category.slug, p.category])).values(),
  ]);

  const visible = $derived(
    (pool ?? []).filter(
      (p) => p.id !== slug && (shown === "all" || p.category.slug === shown)
    )
  );

  async function open() {
    shown = category;
    poolError = null;
    await tick();
    dialog?.showModal();
    if (pool === null) {
      try {
        pool = await listPicturePool();
        if (!pool.some((p) => p.category.slug === category && p.id !== slug)) {
          shown = "all";
        }
      } catch (e) {
        poolError =
          e instanceof ApiError ? e.message : "Nie udało się wczytać puli.";
      }
    }
  }

  async function pick(item: PoolPicture, event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    busy = item.id;
    try {
      const next = await usePoolPicture(slug, item.id);
      onpicked(next);
      dialog?.close();
      showTip(trigger, "Obrazek zmieniony");
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się zmienić obrazka.",
        "bad"
      );
    } finally {
      busy = null;
    }
  }
</script>

<button
  class="ghost cladd-clickable"
  onclick={open}
  type="button"
  bind:this={trigger}
>
  <span>{label}</span>
</button>

<dialog
  aria-labelledby="pool-title"
  class="pool"
  onclose={() => trigger?.focus()}
  bind:this={dialog}
>
  <div class="head">
    <div class="grid gap-1">
      <h2 class="font-semibold text-lg" id="pool-title">
        Wybierz obrazek z&nbsp;puli
      </h2>
      <p class="text-[13px] text-hm-ink-soft">
        Obrazek innego rozwiązania zostanie skopiowany i&nbsp;podpisany jako
        ilustracja poglądowa.
      </p>
    </div>
    <button
      class="ghost cladd-clickable"
      onclick={() => dialog?.close()}
      type="button"
    >
      <span>Zamknij</span>
    </button>
  </div>
  {#if poolError}
    <p class="text-[13px] text-hm-bad">{poolError}</p>
  {:else if pool === null}
    <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
  {:else}
    <label class="flex items-center gap-2 text-[13px]">
      <span class="font-semibold">Kategoria</span>
      <select class="pick" bind:value={shown}>
        <option value="all">Wszystkie</option>
        {#each categories as c (c.slug)}
          <option value={c.slug}>{c.name}</option>
        {/each}
      </select>
    </label>
    {#if visible.length === 0}
      <p class="text-[13px] text-hm-ink-soft">
        W&nbsp;tej kategorii nie ma obrazków do wyboru.
      </p>
    {:else}
      <ul class="grid-list">
        {#each visible as item (item.id)}
          <li>
            <button
              aria-label="Użyj obrazka z rozwiązania {item.title}"
              class="tile cladd-clickable"
              disabled={busy !== null}
              onclick={(event) => pick(item, event)}
              type="button"
            >
              <img
                alt={item.image_alt ?? ""}
                decoding="async"
                height="120"
                loading="lazy"
                src={item.image_card_url}
                width="160"
              >
              <span class="grid gap-0.5 text-left">
                <span class="font-semibold text-[13px]">{item.title}</span>
                <span class="text-hm-ink-soft text-xs"
                  >{busy === item.id ? "Zapisywanie…" : item.image_label}</span
                >
              </span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</dialog>

<style>
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
    background: var(--hm-sunk);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-outline);
    transition: background-color 150ms ease;
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  .pool {
    width: min(880px, calc(100vw - 24px));
    max-height: min(760px, calc(100dvh - 24px));
    padding: 24px 26px;
    margin: auto;
    color: var(--hm-ink);
    background: var(--hm-paper);
    border: 0;
    border-radius: 20px;
    box-shadow:
      0 24px 64px -12px oklch(0.2 0.04 280 / 0.18),
      0 0 0 1px var(--hm-rule);
  }

  .pool[open] {
    display: grid;
    gap: 14px;
  }

  .pool::backdrop {
    background: oklch(0.2 0.04 280 / 0.35);
  }

  .head {
    display: flex;
    gap: 16px;
    align-items: start;
    justify-content: space-between;
  }

  .pick {
    height: 36px;
    padding: 0 8px;
    font-size: 13px;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .grid-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .tile {
    display: grid;
    gap: 8px;
    width: 100%;
    padding: 6px 6px 10px;
    border-radius: 12px;
    transition: background-color 150ms ease;
  }

  .tile:hover {
    background: var(--hm-stamp-wash);
  }

  .tile:disabled {
    opacity: 0.6;
  }

  .tile img {
    display: block;
    width: 100%;
    height: auto;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    background: var(--hm-sunk);
    border-radius: 8px;
  }

  @media (max-width: 899px) {
    .pool {
      padding: 16px 14px;
    }

    .grid-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .ghost,
    .pick {
      height: 44px;
    }
  }
</style>
