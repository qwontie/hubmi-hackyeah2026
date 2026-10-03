<script lang="ts">
  import type { FolderTab } from "$lib/components/hub/types";
  import { plural } from "$lib/format";

  let {
    tabs,
    current,
    oncontext,
  }: {
    tabs: FolderTab[];
    current: string;
    oncontext?: (tab: FolderTab, event: MouseEvent) => void;
  } = $props();

  const height = (tab: FolderTab) =>
    tab.id === "all" ? 84 : Math.min(76 + tab.size * 2, 140);
</script>

<ul class="tabs">
  {#each tabs as tab (tab.id)}
    <li>
      <a
        aria-current={tab.id === current ? "true" : undefined}
        class="tab"
        data-sveltekit-noscroll
        data-sveltekit-replacestate
        href={tab.href}
        oncontextmenu={(event) => oncontext?.(tab, event)}
        style:--h="{height(tab)}px"
      >
        <span class="tt">{tab.title}</span>
        <span class="tn">
          {#if tab.note}
            <span class="tabular">{tab.note}</span>
          {:else if tab.fresh > 0}
            <span class="fresh tabular"
              >{tab.fresh} {plural(tab.fresh, "nowa", "nowe", "nowych")}</span
            >
          {:else if tab.week > 0}
            <span class="tabular">+{tab.week} w&nbsp;tym tyg.</span>
          {:else}
            <span></span>
          {/if}
          <b class="tabular">{tab.size}</b>
        </span>
      </a>
    </li>
  {/each}
</ul>

<style>
  .tabs {
    display: flex;
    flex-direction: column;
    gap: 6px;
    height: 100%;
    padding: 2px 0;
    margin: 0;
    overflow: auto;
    list-style: none;
    scrollbar-width: thin;
  }

  .tab {
    position: relative;
    display: grid;
    grid-template-rows: 1fr auto;
    gap: 6px;
    width: calc(100% - 12px);
    height: var(--h);
    padding: 11px 16px 10px;
    margin-left: 12px;
    color: var(--hm-ink);
    background: var(--hm-tab);
    border-radius: 16px 0 0 16px;
    box-shadow: inset 1px 1px 0 oklch(1 0 0 / 0.35);
    transition:
      margin 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
      width 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
      background-color 150ms ease;
  }

  .tab:hover {
    width: calc(100% - 6px);
    margin-left: 6px;
    background: var(--hm-tab-hover);
  }

  .tab:focus-visible {
    outline-offset: -2px;
  }

  .tab[aria-current="true"] {
    z-index: 1;
    width: 100%;
    margin-left: 0;
    background: var(--hm-board);
    box-shadow: inset 1px 1px 0 oklch(1 0 0 / 0.8);
  }

  .tab[aria-current="true"]::after {
    position: absolute;
    top: 0;
    right: -2px;
    bottom: 0;
    width: 3px;
    content: "";
    background: var(--hm-board);
  }

  .tt {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 14px;
    font-weight: 600;
    line-height: 1.3;
    letter-spacing: -0.01em;
  }

  .tn {
    display: flex;
    gap: 8px;
    align-items: baseline;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-tab-ink-soft);
  }

  .tab[aria-current="true"] .tn {
    color: var(--hm-ink-soft);
  }

  .fresh {
    font-weight: 650;
    color: var(--hm-stamp);
  }

  .tab:not([aria-current="true"]) .fresh {
    color: oklch(0.36 0.17 280);
  }

  .tn b {
    font-size: 22px;
    font-weight: 650;
    line-height: 1;
    color: var(--hm-ink);
    letter-spacing: -0.03em;
  }

  @media (max-width: 899px) {
    .tabs {
      flex-direction: row;
      height: auto;
      padding: 0;
      overflow: visible;
    }

    .tabs li {
      flex: none;
    }

    .tab,
    .tab:hover {
      width: 172px;
      height: 92px;
      margin: 8px 0 0;
      border-radius: 16px 16px 0 0;
    }

    .tab[aria-current="true"] {
      width: 172px;
      height: 100px;
      margin-top: 0;
    }

    .tab[aria-current="true"]::after {
      top: auto;
      right: 0;
      bottom: -2px;
      left: 0;
      width: auto;
      height: 3px;
    }
  }
</style>
