<script lang="ts">
  import { DropdownMenu as DropdownMenuPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: DropdownMenuPrimitive.SeparatorProps = $props();
</script>

<DropdownMenuPrimitive.Separator
  class={cn('-mx-2 my-2 h-px bg-cladd-bg-outline', className)}
  data-slot="dropdown-menu-separator"
  bind:ref
  {...restProps}
/>
