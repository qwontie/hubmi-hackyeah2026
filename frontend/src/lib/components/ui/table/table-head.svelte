<script lang="ts">
  import type { HTMLThAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: WithElementRef<HTMLThAttributes> = $props();
</script>

<th
  class={cn(
		'h-9 bg-clip-padding px-2 text-start align-middle text-cladd-xs font-medium whitespace-nowrap text-cladd-fg-soft uppercase [&:has([role=checkbox])]:pe-0',
		className
	)}
  data-slot="table-head"
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</th>
