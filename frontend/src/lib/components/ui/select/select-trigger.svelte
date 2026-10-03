<script lang="ts">
  import ChevronsUpDownIcon from "@lucide/svelte/icons/chevrons-up-down";
  import { Select as SelectPrimitive } from "bits-ui";
  import { cn, type WithoutChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    size = "default",
    ...restProps
  }: WithoutChild<SelectPrimitive.TriggerProps> & {
    size?: "sm" | "default";
  } = $props();
</script>

<SelectPrimitive.Trigger
  class={cn(
		"cladd-surface cladd-gradient cladd-outline cladd-hoverable cladd-clickable cladd-focusable flex w-fit items-center justify-between gap-2 rounded-cladd-md px-2.5 text-cladd-xs font-semibold whitespace-nowrap text-cladd-fg select-none disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:outline-destructive data-[placeholder]:text-cladd-fg-softer data-[size=default]:h-cladd-md data-[size=sm]:h-cladd-sm *:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-cladd-fg-softer",
		className
	)}
  data-size={size}
  data-slot="select-trigger"
  bind:ref
  {...restProps}
>
  {@render children?.()}
  <ChevronsUpDownIcon class="size-3.5 text-cladd-fg-softer" />
</SelectPrimitive.Trigger>
