<script lang="ts">
  import type { AdminNeed } from "$lib/api/admin";
  import {
    clock,
    nbsp,
    plural,
    powiatName,
    registerNumber,
    statusLabel,
    when,
  } from "$lib/format";
  import { inbox } from "$lib/live/inbox.svelte";
  import { powiats } from "$lib/live/powiats.svelte";

  let {
    needs,
    current,
    hrefFor,
    showFolder,
    oncontext,
  }: {
    needs: AdminNeed[];
    current: string | null;
    hrefFor: (need: AdminNeed) => string;
    showFolder: boolean;
    oncontext?: (need: AdminNeed, event: MouseEvent) => void;
  } = $props();

  const today = new Date().toDateString();
  const folderTitle = (ref: { id: string; title: string }) =>
    inbox.clusters.find((c) => c.id === ref.id)?.title ?? ref.title;
  const stamp = (iso: string) =>
    new Date(iso).toDateString() === today ? clock(iso) : when(iso);
</script>

<ol aria-label="Wpisy w dzienniku" class="rows">
  {#each needs as need (need.id)}
    <li>
      <a
        aria-current={need.id === current ? "true" : undefined}
        class={["row", `is-${need.status}`, inbox.unopened(need) && "unseen", inbox.arrived.has(need.id) && "hm-arrive"]}
        data-id={need.id}
        data-sveltekit-noscroll
        data-sveltekit-replacestate
        href={hrefFor(need)}
        oncontextmenu={(event) => oncontext?.(need, event)}
      >
        <span class="nr mono-num">{registerNumber(need.number)}</span>
        <span class="grid min-w-0 gap-[3px]">
          <span class="tx">{nbsp(need.text)}</span>
          <span class="text-hm-ink-soft text-xs tabular">
            {stamp(need.created_at)}{need.powiat ? ` · ${powiatName(need.powiat, powiats.names)}` : ""}{showFolder && need.cluster ? ` · ${folderTitle(need.cluster)}` : ""}{(need.unread ?? 0) > 0 ? ` · ${need.unread} ${plural(need.unread ?? 0, "nowa wiadomość", "nowe wiadomości", "nowych wiadomości")}` : ""}
          </span>
        </span>
        <span class="st">{statusLabel[need.status]}</span>
      </a>
    </li>
  {/each}
</ol>

<style>
  .rows {
    position: relative;
    min-height: 0;
    padding: 0 0 8px;
    margin: 0;
    overflow: auto;
    list-style: none;
  }

  .row {
    position: relative;
    display: grid;
    grid-template-columns: 50px minmax(0, 1fr) 104px;
    gap: 12px;
    align-items: baseline;
    min-height: 64px;
    padding: 11px 12px 11px 4px;
    border-bottom: 1px solid var(--hm-rule);
    transition: background-color 150ms ease;
  }

  .row:hover {
    background: color-mix(in oklab, var(--hm-stamp) 5%, transparent);
  }

  .row:focus-visible {
    outline-offset: -2px;
    border-radius: 12px;
  }

  .row[aria-current="true"] {
    background: var(--hm-stamp-wash);
    border-bottom-color: transparent;
    border-radius: 12px;
  }

  .nr {
    padding-left: 8px;
    font-size: 13px;
    color: var(--hm-ink-soft);
  }

  .unseen .nr {
    font-weight: 650;
    color: var(--hm-stamp);
  }

  .tx {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 13.5px;
    line-height: 1.42;
  }

  .unseen .tx {
    font-weight: 560;
  }

  .is-closed .tx,
  .is-junk .tx {
    color: var(--hm-ink-soft);
  }

  .st {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
  }

  .st::before {
    width: 6px;
    height: 6px;
    content: "";
    background: currentColor;
    border-radius: 50%;
  }

  .is-new .st {
    color: var(--hm-stamp);
  }

  .is-answered .st {
    color: var(--hm-ok);
  }

  @media (max-width: 899px) {
    .row {
      grid-template-columns: 44px minmax(0, 1fr);
      padding-right: 8px;
    }

    .st {
      grid-column: 2;
    }
  }
</style>
