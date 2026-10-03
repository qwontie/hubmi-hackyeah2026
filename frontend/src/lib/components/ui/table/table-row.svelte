<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: WithElementRef<HTMLAttributes<HTMLTableRowElement>> = $props();
</script>

<tr
  class={cn(
		'border-b border-cladd-bg-outline transition-colors duration-200 data-[state=selected]:bg-cladd-surface-hover hover:[&,&>svelte-css-wrapper]:[&>th,td]:bg-cladd-surface-hover',
		className
	)}
  data-slot="table-row"
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</tr>
