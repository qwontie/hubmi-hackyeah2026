<script lang="ts">
  import { Tabs as TabsPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: TabsPrimitive.ListProps = $props();
</script>

<TabsPrimitive.List
  class={cn(
		'cladd-surface cladd-gradient cladd-outline scrollbar-none inline-flex h-9 items-center gap-0.5 overflow-x-auto rounded-full p-1 text-cladd-fg',
		className
	)}
  data-slot="tabs-list"
  bind:ref
  {...restProps}
/>
