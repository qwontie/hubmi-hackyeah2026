<script lang="ts">
  import { Tabs as TabsPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: TabsPrimitive.TriggerProps = $props();
</script>

<TabsPrimitive.Trigger
  class={cn(
		"cladd-segment cladd-focusable inline-flex h-full shrink-0 items-center justify-center gap-1.5 rounded-full px-2.5 text-cladd-xs font-semibold whitespace-nowrap text-cladd-fg disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
		className
	)}
  data-slot="tabs-trigger"
  bind:ref
  {...restProps}
/>
