<script lang="ts">
  import CheckIcon from "@lucide/svelte/icons/check";
  import { Select as SelectPrimitive } from "bits-ui";
  import { cn, type WithoutChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    value,
    label,
    children: childrenProp,
    ...restProps
  }: WithoutChild<SelectPrimitive.ItemProps> = $props();
</script>

<SelectPrimitive.Item
  class={cn(
		"relative flex min-h-cladd-lg cursor-default items-center gap-2 rounded-full py-1 ps-3 pe-9 text-cladd-xs font-medium outline-hidden transition-[background-color,box-shadow] duration-200 select-none data-highlighted:bg-cladd-surface-next data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[selected]:bg-cladd-surface-next data-[selected]:shadow-cladd-outline [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-cladd-fg-soft *:[span]:last:flex *:[span]:last:items-center *:[span]:last:gap-2",
		className
	)}
  data-slot="select-item"
  {value}
  bind:ref
  {...restProps}
>
  {#snippet children({ selected, highlighted })}
    <span class="absolute end-3 flex size-4 items-center justify-center">
      {#if selected}
        <CheckIcon class="size-4 text-cladd-fg" />
      {/if}
    </span>
    {#if childrenProp}
      {@render childrenProp({ selected, highlighted })}
    {:else}
      {label || value}
    {/if}
  {/snippet}
</SelectPrimitive.Item>
