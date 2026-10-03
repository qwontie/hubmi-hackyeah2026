<script lang="ts">
  import type { Snippet } from "svelte";
  import { cn } from "$lib/utils";

  let {
    title,
    count,
    actions,
    children,
    class: className,
  }: {
    title: string;
    count?: number | string;
    actions?: Snippet;
    children?: Snippet;
    class?: string;
  } = $props();
</script>

<svelte:head>
  <title>{title} · HubMi</title>
</svelte:head>

<header
  class={cn(
    "flex min-h-7 flex-wrap items-center justify-between gap-x-6 gap-y-2 pb-4",
    className
  )}
>
  <div class="flex min-w-0 items-baseline gap-2.5">
    <h1 class="clamp-line font-semibold text-hm-xl tracking-tight">{title}</h1>
    {#if count !== undefined}
      <span class="tabular text-cladd-fg-soft text-hm-base">{count}</span>
    {/if}
    {@render children?.()}
  </div>
  {#if actions}
    <div class="flex flex-wrap items-center gap-2">{@render actions()}</div>
  {/if}
</header>
