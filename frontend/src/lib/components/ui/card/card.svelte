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
  class={cn(
		'cladd-surface cladd-outline flex flex-col gap-4 rounded-cladd-panel py-4 text-cladd-fg *:[form]:flex *:[form]:flex-col *:[form]:gap-4',
		className
	)}
  data-slot="card"
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</div>
