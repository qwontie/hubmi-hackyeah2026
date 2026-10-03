<script lang="ts">
  import CheckIcon from "@lucide/svelte/icons/check";
  import MinusIcon from "@lucide/svelte/icons/minus";
  import { DropdownMenu as DropdownMenuPrimitive } from "bits-ui";
  import type { Snippet } from "svelte";
  import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    checked = $bindable(false),
    indeterminate = $bindable(false),
    class: className,
    children: childrenProp,
    ...restProps
  }: WithoutChildrenOrChild<DropdownMenuPrimitive.CheckboxItemProps> & {
    children?: Snippet;
  } = $props();
</script>

<DropdownMenuPrimitive.CheckboxItem
  class={cn(
		"relative flex min-h-cladd-lg cursor-default items-center gap-2 rounded-full py-1 ps-9 pe-3 text-cladd-xs font-medium outline-hidden transition-[background-color,box-shadow] duration-200 select-none data-highlighted:bg-cladd-surface-next data-[disabled]:pointer-events-none data-[disabled]:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-cladd-fg-soft",
		className
	)}
  data-slot="dropdown-menu-checkbox-item"
  bind:checked
  bind:indeterminate
  bind:ref
  {...restProps}
>
  {#snippet children({ checked, indeterminate })}
    <span
      class="pointer-events-none absolute start-3 flex size-4 items-center justify-center"
    >
      {#if indeterminate}
        <MinusIcon class="size-4" />
      {:else}
        <CheckIcon class={cn('size-4', !checked && 'text-transparent')} />
      {/if}
    </span>
    {@render childrenProp?.()}
  {/snippet}
</DropdownMenuPrimitive.CheckboxItem>
