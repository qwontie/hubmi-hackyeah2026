<script lang="ts">
  import CircleIcon from "@lucide/svelte/icons/circle";
  import { DropdownMenu as DropdownMenuPrimitive } from "bits-ui";
  import { cn, type WithoutChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children: childrenProp,
    ...restProps
  }: WithoutChild<DropdownMenuPrimitive.RadioItemProps> = $props();
</script>

<DropdownMenuPrimitive.RadioItem
  class={cn(
		"relative flex min-h-cladd-lg cursor-default items-center gap-2 rounded-full py-1 ps-9 pe-3 text-cladd-xs font-medium outline-hidden transition-[background-color,box-shadow] duration-200 select-none data-highlighted:bg-cladd-surface-next data-[disabled]:pointer-events-none data-[disabled]:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-cladd-fg-soft",
		className
	)}
  data-slot="dropdown-menu-radio-item"
  bind:ref
  {...restProps}
>
  {#snippet children({ checked })}
    <span
      class="pointer-events-none absolute start-3 flex size-4 items-center justify-center"
    >
      {#if checked}
        <CircleIcon class="size-2 fill-current" />
      {/if}
    </span>
    {@render childrenProp?.({ checked })}
  {/snippet}
</DropdownMenuPrimitive.RadioItem>
