<script lang="ts">
  import ChevronRightIcon from "@lucide/svelte/icons/chevron-right";
  import { ContextMenu as ContextMenuPrimitive } from "bits-ui";
  import { cn, type WithoutChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    inset,
    children,
    ...restProps
  }: WithoutChild<ContextMenuPrimitive.SubTriggerProps> & {
    inset?: boolean;
  } = $props();
</script>

<ContextMenuPrimitive.SubTrigger
  class={cn(
		"relative flex min-h-cladd-lg cursor-default items-center gap-2 rounded-full px-3 py-1 text-cladd-xs font-medium outline-hidden transition-[background-color,box-shadow] duration-200 select-none data-highlighted:bg-cladd-surface-next data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[inset]:ps-8 data-[inset]:ps-9 data-[state=open]:bg-cladd-surface-next [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-cladd-fg-soft",
		className
	)}
  data-inset={inset}
  data-slot="context-menu-sub-trigger"
  bind:ref
  {...restProps}
>
  {@render children?.()}
  <ChevronRightIcon class="ms-auto" />
</ContextMenuPrimitive.SubTrigger>
