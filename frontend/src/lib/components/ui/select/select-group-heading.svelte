<script lang="ts">
  import { Select as SelectPrimitive } from "bits-ui";
  import type { ComponentProps } from "svelte";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: ComponentProps<typeof SelectPrimitive.GroupHeading> = $props();
</script>

<SelectPrimitive.GroupHeading
  class={cn('cladd-section-title px-3 pt-2 pb-1.5 data-[inset]:ps-9', className)}
  data-slot="select-group-heading"
  bind:ref
  {...restProps}
>
  {@render children?.()}
</SelectPrimitive.GroupHeading>
