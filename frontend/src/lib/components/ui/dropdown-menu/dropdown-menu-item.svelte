<script lang="ts">
  import { DropdownMenu as DropdownMenuPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    inset,
    variant = "default",
    ...restProps
  }: DropdownMenuPrimitive.ItemProps & {
    inset?: boolean;
    variant?: "default" | "destructive";
    asChild?: boolean;
  } = $props();
</script>

<DropdownMenuPrimitive.Item
  class={cn(
		"relative flex min-h-cladd-lg cursor-default items-center gap-2 rounded-full px-3 py-1 text-cladd-xs font-medium outline-hidden transition-[background-color,box-shadow] duration-200 select-none data-highlighted:bg-cladd-surface-next data-[disabled]:pointer-events-none data-[disabled]:opacity-40 data-[inset]:ps-8 data-[inset]:ps-9 data-[variant=destructive]:text-destructive data-[variant=destructive]:data-highlighted:bg-destructive/12 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-cladd-fg-soft data-[variant=destructive]:*:[svg]:!text-destructive",
		className
	)}
  data-inset={inset}
  data-slot="dropdown-menu-item"
  data-variant={variant}
  bind:ref
  {...restProps}
/>
