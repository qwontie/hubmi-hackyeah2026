<script lang="ts">
  import type { AdminNeed } from "$lib/api/admin";
  import { plural } from "$lib/format";

  interface Day {
    needs: number;
    nothing_fits: number;
    start: string;
  }

  let {
    days,
    needs,
    names,
  }: {
    days: Day[];
    needs: AdminNeed[] | null;
    names: Map<string, string>;
  } = $props();

  let active = $state<number | null>(null);
  let focusIndex = $state(-1);
  let chart = $state<HTMLFieldSetElement | null>(null);

  const ZONE = "Europe/Warsaw";
  const dayKey = (iso: string) =>
    new Date(iso).toLocaleDateString("en-CA", { timeZone: ZONE });

  const maxDay = $derived(Math.max(1, ...days.map((d) => d.needs)));
  const tabStop = $derived(
    focusIndex >= 0 && focusIndex < days.length ? focusIndex : days.length - 1
  );

  const byDay = $derived.by(() => {
    const out = new Map<string, Map<string, number>>();
    for (const n of needs ?? []) {
      const key = dayKey(n.created_at);
      const cats = out.get(key) ?? new Map<string, number>();
      const cat = n.category_slug ?? "";
      cats.set(cat, (cats.get(cat) ?? 0) + 1);
      out.set(key, cats);
    }
    return out;
  });

  const label = (iso: string) =>
    new Date(`${iso}T12:00:00`)
      .toLocaleDateString("pl-PL", {
        day: "numeric",
        month: "long",
        weekday: "short",
      })
      .replace(" ", " ");

  const shortLabel = (iso: string) =>
    new Date(`${iso}T12:00:00`).toLocaleDateString("pl-PL", {
      day: "numeric",
      month: "short",
    });

  function parts(day: Day) {
    const cats = byDay.get(day.start);
    if (!cats) {
      return [];
    }
    return [...cats.entries()]
      .map(([slug, count]) => ({
        count,
        name: slug
          ? (names.get(slug) ?? slug.replaceAll("-", " "))
          : "Bez obszaru",
        slug,
      }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "pl"));
  }

  const needWord = (n: number) => plural(n, "potrzeba", "potrzeby", "potrzeb");

  function describe(day: Day) {
    const list = parts(day)
      .map((p) => `${p.name} ${p.count}`)
      .join(", ");
    const none =
      day.nothing_fits > 0
        ? `, w tym nic nie pasowało: ${day.nothing_fits}`
        : "";
    return `${label(day.start)}: ${day.needs} ${needWord(day.needs)}${list ? `. ${list}` : ""}${none}`;
  }

  function keydown(event: KeyboardEvent, index: number) {
    const moves: Record<string, number> = {
      ArrowLeft: index - 1,
      ArrowRight: index + 1,
      End: days.length - 1,
      Home: 0,
    };
    if (!(event.key in moves)) {
      if (event.key === "Escape") {
        active = null;
      }
      return;
    }
    event.preventDefault();
    const next = Math.max(0, Math.min(days.length - 1, moves[event.key]));
    focusIndex = next;
    chart?.querySelectorAll<HTMLButtonElement>(".col")[next]?.focus();
  }

  const shown = $derived(active === null ? null : (days[active] ?? null));
  const shownParts = $derived(shown ? parts(shown) : []);
  const maxPart = $derived(Math.max(1, ...shownParts.map((p) => p.count)));
  const anchor = $derived(
    active === null || days.length === 0
      ? 50
      : ((active + 0.5) / days.length) * 100
  );
</script>

<div class="wrap">
  <fieldset
    class="chart"
    onpointerleave={() => {
      if (!chart?.contains(document.activeElement)) {
        active = null;
      }
    }}
    bind:this={chart}
  >
    <legend class="sr-only">
      Nowe potrzeby w&nbsp;kolejnych dniach. Strzałki w&nbsp;lewo
      i&nbsp;w&nbsp;prawo przechodzą między dniami.
    </legend>
    {#each days as d, i (d.start)}
      <button
        aria-label={describe(d)}
        class={["col", active === i && "on"]}
        onblur={() => {
          if (active === i) {
            active = null;
          }
        }}
        onfocus={() => {
          active = i;
          focusIndex = i;
        }}
        onkeydown={(event) => keydown(event, i)}
        onpointerenter={() => {
          active = i;
        }}
        tabindex={i === tabStop ? 0 : -1}
        type="button"
      >
        <i style:height="{(d.needs / maxDay) * 100}%">
          {#if d.nothing_fits > 0}
            <b
              style:height="{(d.nothing_fits / Math.max(1, d.needs)) * 100}%"
            ></b>
          {/if}
        </i>
      </button>
    {/each}
  </fieldset>

  {#if shown}
    <div
      aria-hidden="true"
      class={["tip", anchor > 70 && "right", anchor < 30 && "left"]}
      style:--x="{anchor}%"
    >
      <p class="head">
        <b>{label(shown.start)}</b>
        <span class="tabular">{shown.needs} {needWord(shown.needs)}</span>
      </p>
      {#if shownParts.length > 0}
        <ol>
          {#each shownParts as p (p.slug)}
            <li>
              <span class="name">{p.name}</span>
              <span class="tabular">{p.count}</span>
              <i class="pbar" style:width="{(p.count / maxPart) * 100}%"></i>
            </li>
          {/each}
        </ol>
      {:else if shown.needs > 0}
        <p class="none">Obszary tych potrzeb jeszcze się wczytują.</p>
      {/if}
      {#if shown.nothing_fits > 0}
        <p class="none tabular">Nic nie pasowało: {shown.nothing_fits}</p>
      {/if}
    </div>
  {/if}
</div>

<div aria-hidden="true" class="axis">
  <span>{days[0] ? shortLabel(days[0].start) : ""}</span>
  <span>najwięcej {maxDay} dziennie</span>
  <span>{days.at(-1) ? shortLabel(days.at(-1)?.start ?? "") : ""}</span>
</div>

{#if days.some((d) => d.nothing_fits > 0)}
  <p class="legend">
    <span><i aria-hidden="true" class="sw all"></i>nowe potrzeby</span>
    <span
      ><i aria-hidden="true" class="sw none"></i>w&nbsp;tym nic nie
      pasowało</span
    >
  </p>
{/if}

<style>
  .wrap {
    position: relative;
  }

  .chart {
    display: flex;
    gap: 3px;
    align-items: flex-end;
    min-width: 0;
    height: 160px;
    padding: 0;
    margin: 0;
    border: 0;
  }

  .col {
    display: flex;
    flex: 1;
    align-items: flex-end;
    min-width: 0;
    height: 100%;
    padding: 0;
    cursor: default;
    border-radius: 5px 5px 2px 2px;
  }

  .col:focus-visible {
    outline-offset: 2px;
  }

  .col i {
    position: relative;
    display: flex;
    align-items: flex-end;
    width: 100%;
    min-height: 2px;
    overflow: hidden;
    background: var(--hm-stamp);
    border-radius: 4px 4px 1px 1px;
    transition: background-color 150ms ease;
  }

  .col b {
    display: block;
    width: 100%;
    background: var(--hm-tab);
  }

  .chart:has(.on) .col:not(.on) i {
    background: color-mix(in oklab, var(--hm-stamp) 45%, var(--hm-board));
  }

  .tip {
    position: absolute;
    bottom: calc(100% + 10px);
    left: var(--x);
    z-index: 5;
    width: max-content;
    min-width: 220px;
    max-width: 300px;
    padding: 12px 14px;
    pointer-events: none;
    background: var(--hm-paper);
    border-radius: 18px;
    box-shadow:
      0 24px 64px -12px oklch(0.2 0.04 280 / 0.22),
      0 0 0 1px var(--hm-rule);
    translate: -50% 0;
    animation: pop 220ms cubic-bezier(0, 1, 0, 1.025);
  }

  .tip.right {
    translate: -100% 0;
  }

  .tip.left {
    translate: 0 0;
  }

  @keyframes pop {
    from {
      opacity: 0;
      scale: 0.96;
    }
  }

  .head {
    display: flex;
    gap: 16px;
    align-items: baseline;
    justify-content: space-between;
    margin: 0 0 8px;
    font-size: 13px;
  }

  .head span {
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  ol {
    display: grid;
    gap: 6px;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 3px 12px;
    font-size: 13px;
  }

  li .name {
    min-width: 0;
  }

  .pbar {
    grid-column: 1 / -1;
    height: 4px;
    background: var(--hm-stamp);
    border-radius: 4px;
  }

  .none {
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  .axis {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  .legend span {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }

  .sw {
    width: 10px;
    height: 10px;
    border-radius: 3px;
  }

  .sw.all {
    background: var(--hm-stamp);
  }

  .sw.none {
    background: var(--hm-tab);
    box-shadow: inset 0 0 0 1px var(--hm-stamp);
  }

  @media (max-width: 899px) {
    .chart {
      gap: 1px;
      height: 120px;
    }

    .tip {
      min-width: 200px;
      max-width: calc(100vw - 48px);
    }
  }
</style>
