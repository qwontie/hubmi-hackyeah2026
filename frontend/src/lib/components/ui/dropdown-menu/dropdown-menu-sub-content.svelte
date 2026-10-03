<script lang="ts">
  import { DropdownMenu as DropdownMenuPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: DropdownMenuPrimitive.SubContentProps = $props();
</script>

<DropdownMenuPrimitive.SubContent
  class={cn(
		'cladd-surface cladd-gradient cladd-outline cladd-level-1 cladd-anim-popover z-50 min-w-[10rem] origin-(--bits-dropdown-menu-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-cladd-popover p-2 text-cladd-fg shadow-cladd-popover outline-none',
		className
	)}
  data-slot="dropdown-menu-sub-content"
  bind:ref
  {...restProps}
/>
