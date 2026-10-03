<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: WithElementRef<HTMLAttributes<HTMLDivElement>> = $props();
</script>

<div
  class={cn('flex flex-col gap-1.5 text-start', className)}
  data-slot="dialog-header"
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</div>
