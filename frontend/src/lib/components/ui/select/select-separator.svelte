<script lang="ts">
  import type { Separator as SeparatorPrimitive } from "bits-ui";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: SeparatorPrimitive.RootProps = $props();
</script>

<Separator
  class={cn('pointer-events-none -mx-2 my-2 h-px bg-cladd-bg-outline', className)}
  data-slot="select-separator"
  bind:ref
  {...restProps}
/>
