<script lang="ts">
  import { ContextMenu as ContextMenuPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    inset,
    ...restProps
  }: ContextMenuPrimitive.GroupHeadingProps & {
    inset?: boolean;
  } = $props();
</script>

<ContextMenuPrimitive.GroupHeading
  class={cn('cladd-section-title px-3 pt-2 pb-1.5 data-[inset]:ps-8 data-[inset]:ps-9', className)}
  data-inset={inset}
  data-slot="context-menu-group-heading"
  bind:ref
  {...restProps}
/>
