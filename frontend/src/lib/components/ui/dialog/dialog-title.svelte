<script lang="ts">
  import { Dialog as DialogPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: DialogPrimitive.TitleProps = $props();
</script>

<DialogPrimitive.Title
  class={cn('pe-8 text-cladd-md leading-tight font-semibold', className)}
  data-slot="dialog-title"
  bind:ref
  {...restProps}
/>
