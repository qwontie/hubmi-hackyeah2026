<script lang="ts">
  import { cn } from "$lib/utils";

  let {
    label,
    value,
    tone = "plain",
    layout = "inline",
    class: className,
  }: {
    label: string;
    value: string | number;
    tone?: "plain" | "signal" | "bad" | "ok" | "soft";
    layout?: "inline" | "block";
    class?: string;
  } = $props();

  const tones = {
    bad: "text-bad",
    ok: "text-ok",
    plain: "text-cladd-fg",
    signal: "text-signal",
    soft: "text-cladd-fg-soft",
  };
</script>

{#if layout === "block"}
  <div class={cn("flex min-w-0 flex-col gap-0.5", className)}>
    <span
      class={cn(
        "tabular font-semibold text-hm-xl leading-none",
        tones[tone]
      )}
      >{value}</span
    >
    <span class="clamp-line text-cladd-fg-soft text-hm-xs">{label}</span>
  </div>
{:else}
  <span
    class={cn(
      "inline-flex items-baseline gap-1.5 whitespace-nowrap",
      className
    )}
  >
    <span class="text-cladd-fg-soft text-hm-xs">{label}</span>
    <span class={cn("tabular font-medium", tones[tone])}>{value}</span>
  </span>
{/if}
