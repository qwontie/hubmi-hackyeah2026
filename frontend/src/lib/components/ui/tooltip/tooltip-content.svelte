<script lang="ts">
  import { Tooltip as TooltipPrimitive } from "bits-ui";
  import type { ComponentProps } from "svelte";
  import type { WithoutChildrenOrChild } from "$lib/utils.js";
  import { cn } from "$lib/utils.js";
  import TooltipPortal from "./tooltip-portal.svelte";

  let {
    ref = $bindable(null),
    class: className,
    sideOffset = 6,
    side = "top",
    children,
    portalProps,
    ...restProps
  }: TooltipPrimitive.ContentProps & {
    portalProps?: WithoutChildrenOrChild<ComponentProps<typeof TooltipPortal>>;
  } = $props();
</script>

<TooltipPortal {...portalProps}>
  <TooltipPrimitive.Content
    class={cn(
			'cladd-surface cladd-gradient cladd-outline cladd-level-5 cladd-anim-tooltip z-50 w-fit max-w-72 origin-(--bits-tooltip-content-transform-origin) rounded-cladd-tooltip px-2 py-1 text-cladd-xs leading-normal font-medium text-balance text-cladd-fg',
			className
		)}
    data-slot="tooltip-content"
    {side}
    {sideOffset}
    bind:ref
    {...restProps}
  >
    {@render children?.()}
  </TooltipPrimitive.Content>
</TooltipPortal>
