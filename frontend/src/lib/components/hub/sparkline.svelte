<script lang="ts">
  let {
    values,
    width = 96,
    height = 26,
  }: { values: number[]; width?: number; height?: number } = $props();

  const points = $derived.by(() => {
    if (values.length < 2) {
      return "";
    }
    const max = Math.max(...values, 1);
    const step = width / (values.length - 1);
    return values
      .map(
        (v, i) =>
          `${(i * step).toFixed(1)},${(height - 1.5 - (v / max) * (height - 3)).toFixed(1)}`
      )
      .join(" ");
  });
</script>

{#if points}
  <svg
    aria-hidden="true"
    class="text-hm-stamp"
    {height}
    viewBox="0 0 {width} {height}"
    {width}
  >
    <polyline
      fill="none"
      {points}
      stroke="currentColor"
      stroke-linecap="round"
      stroke-linejoin="round"
      stroke-width="1.5"
    />
  </svg>
{/if}
