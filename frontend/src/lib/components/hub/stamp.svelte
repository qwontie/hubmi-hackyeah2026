<script lang="ts">
  import { clock, dayWords, registerNumber } from "$lib/format";

  let { at, number }: { at: string; number?: number | null } = $props();

  const nr = $derived(registerNumber(number));
  const label = $derived(
    `Wpłynęło ${dayWords(at)}, godzina ${clock(at)}${nr ? `, numer ${nr}` : ""}`
  );
</script>

<div aria-label={label} class="stamp hm-land" role="img">
  <div>
    <span class="stamp-word">Wpłynęło</span>
    <span class="font-semibold text-sm">{dayWords(at)}</span>
    <span class="mono-num text-xs"
      >godz. {clock(at)}{nr ? ` · HUB/${nr}` : ""}</span
    >
  </div>
</div>

<style>
  .stamp {
    flex: none;
    padding: 3px;
    color: var(--hm-stamp);
    text-align: center;
    border: 2px solid currentColor;
    border-radius: 8px;
    rotate: -3deg;
  }

  .stamp > div {
    display: grid;
    gap: 1px;
    padding: 6px 12px 7px;
    border: 1px solid currentColor;
    border-radius: 5px;
  }
</style>
