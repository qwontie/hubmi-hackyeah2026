<script lang="ts">
  import { ContextMenu as ContextMenuPrimitive } from "bits-ui";
  import type { ComponentProps } from "svelte";
  import type { WithoutChildrenOrChild } from "$lib/utils.js";
  import { cn } from "$lib/utils.js";
  import ContextMenuPortal from "./context-menu-portal.svelte";

  let {
    ref = $bindable(null),
    portalProps,
    class: className,
    ...restProps
  }: ContextMenuPrimitive.ContentProps & {
    portalProps?: WithoutChildrenOrChild<
      ComponentProps<typeof ContextMenuPortal>
    >;
  } = $props();
</script>

<ContextMenuPortal {...portalProps}>
  <ContextMenuPrimitive.Content
    class={cn(
			'cladd-surface cladd-gradient cladd-outline cladd-level-1 cladd-anim-popover z-50 max-h-(--bits-context-menu-content-available-height) min-w-[10rem] origin-(--bits-context-menu-content-transform-origin) overflow-x-hidden overflow-y-auto rounded-cladd-popover p-2 text-cladd-fg shadow-cladd-popover outline-none',
			className
		)}
    data-slot="context-menu-content"
    bind:ref
    {...restProps}
  />
</ContextMenuPortal>
