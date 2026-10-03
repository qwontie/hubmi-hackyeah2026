<script lang="ts">
  import { Dialog as DialogPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: DialogPrimitive.DescriptionProps = $props();
</script>

<DialogPrimitive.Description
  class={cn('text-cladd-sm leading-relaxed text-cladd-fg-soft', className)}
  data-slot="dialog-description"
  bind:ref
  {...restProps}
/>
