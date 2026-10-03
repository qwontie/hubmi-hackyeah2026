<script lang="ts">
  import { tick } from "svelte";
  import type { MenuItem } from "$lib/components/hub/types";

  let items = $state<(MenuItem | "-")[]>([]);
  let x = $state(0);
  let y = $state(0);
  let open = $state(false);
  let menu = $state<HTMLDivElement | null>(null);
  let returnTo: HTMLElement | null = null;

  export async function show(
    event: MouseEvent | KeyboardEvent,
    next: (MenuItem | "-")[],
    anchor?: HTMLElement | null
  ) {
    event.preventDefault();
    returnTo =
      anchor ??
      (event.currentTarget instanceof HTMLElement ? event.currentTarget : null);
    items = next;
    if (event instanceof MouseEvent && event.clientX > 0) {
      x = event.clientX;
      y = event.clientY;
    } else if (returnTo) {
      const r = returnTo.getBoundingClientRect();
      x = r.left + 24;
      y = r.top + r.height / 2;
    }
    open = true;
    await tick();
    if (menu) {
      const r = menu.getBoundingClientRect();
      x = Math.max(8, Math.min(x, innerWidth - r.width - 8));
      y = Math.max(8, Math.min(y, innerHeight - r.height - 8));
      menu.querySelector("button")?.focus();
    }
  }

  function hide(restore = true) {
    open = false;
    if (restore) {
      returnTo?.focus();
    }
  }

  function keydown(event: KeyboardEvent) {
    if (!(open && menu)) {
      return;
    }
    const buttons = [...menu.querySelectorAll("button")];
    const index = buttons.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      hide();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      buttons[(index + 1) % buttons.length]?.focus();
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      buttons[(index - 1 + buttons.length) % buttons.length]?.focus();
    } else if (event.key === "Tab") {
      hide(false);
    }
  }

  function pointerdown(event: PointerEvent) {
    if (open && menu && !menu.contains(event.target as Node)) {
      hide(false);
    }
  }
</script>

<svelte:window
  onblur={() => open && hide(false)}
  onkeydown={keydown}
  onpointerdown={pointerdown}
  onresize={() => open && hide(false)}
/>

{#if open}
  <div
    class="menu"
    role="menu"
    bind:this={menu}
    style:left="{x}px"
    style:top="{y}px"
  >
    {#each items as item, i (i)}
      {#if item === "-"}
        <hr class="sep">
      {:else}
        <button
          class={[item.tone === "bad" && "bad"]}
          onclick={() => {
            hide();
            item.run();
          }}
          role="menuitem"
          type="button"
        >
          <span>{item.label}</span>
          {#if item.hint}
            <kbd>{item.hint}</kbd>
          {/if}
        </button>
      {/if}
    {/each}
  </div>
{/if}

<style>
  .menu {
    position: fixed;
    z-index: 60;
    min-width: 240px;
    padding: 6px;
    background: var(--hm-paper);
    border-radius: 18px;
    box-shadow:
      0 24px 64px -12px oklch(0.2 0.04 280 / 0.22),
      0 0 0 1px var(--hm-rule);
    transform-origin: top left;
    animation: pop 220ms cubic-bezier(0, 1, 0, 1.025);
  }

  @keyframes pop {
    from {
      opacity: 0;
      scale: 0.92;
    }
  }

  button {
    display: flex;
    gap: 16px;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    min-height: 36px;
    padding: 0 12px;
    font-size: 13px;
    color: var(--hm-ink);
    text-align: left;
    border-radius: 12px;
  }

  button:hover,
  button:focus-visible {
    outline: none;
    background: var(--hm-stamp-wash);
  }

  button.bad {
    color: var(--hm-bad);
  }

  kbd {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--hm-ink-soft);
  }

  @media (max-width: 899px), (pointer: coarse) {
    button {
      min-height: 44px;
    }
  }

  .sep {
    height: 1px;
    margin: 4px 8px;
    background: var(--hm-rule);
    border: 0;
  }
</style>
