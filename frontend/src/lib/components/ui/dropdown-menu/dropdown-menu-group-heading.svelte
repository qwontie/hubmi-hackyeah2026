<script lang="ts">
  import { DropdownMenu as DropdownMenuPrimitive } from "bits-ui";
  import type { ComponentProps } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    inset,
    ...restProps
  }: ComponentProps<typeof DropdownMenuPrimitive.GroupHeading> & {
    inset?: boolean;
  } = $props();
</script>

<DropdownMenuPrimitive.GroupHeading
  class={cn('cladd-section-title px-3 pt-2 pb-1.5 data-[inset]:ps-8 data-[inset]:ps-9', className)}
  data-inset={inset}
  data-slot="dropdown-menu-group-heading"
  bind:ref
  {...restProps}
/>
