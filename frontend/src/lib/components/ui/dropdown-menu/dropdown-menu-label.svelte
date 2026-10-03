<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    inset,
    children,
    ...restProps
  }: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
    inset?: boolean;
  } = $props();
</script>

<div
  class={cn('cladd-section-title px-3 pt-2 pb-1.5 data-[inset]:ps-8 data-[inset]:ps-9', className)}
  data-inset={inset}
  data-slot="dropdown-menu-label"
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</div>
