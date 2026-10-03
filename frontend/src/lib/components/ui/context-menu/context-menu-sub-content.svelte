<script lang="ts">
  import { ContextMenu as ContextMenuPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: ContextMenuPrimitive.SubContentProps = $props();
</script>

<ContextMenuPrimitive.SubContent
  class={cn(
		'cladd-surface cladd-gradient cladd-outline cladd-level-1 cladd-anim-popover z-50 min-w-[10rem] origin-(--bits-context-menu-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-cladd-popover p-2 text-cladd-fg shadow-cladd-popover outline-none',
		className
	)}
  data-slot="context-menu-sub-content"
  bind:ref
  {...restProps}
/>
