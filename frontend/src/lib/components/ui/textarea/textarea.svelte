<script lang="ts">
  import type { HTMLTextareaAttributes } from "svelte/elements";
  import { cn, type WithElementRef, type WithoutChildren } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    value = $bindable(),
    class: className,
    "data-slot": dataSlot = "textarea",
    ...restProps
  }: WithoutChildren<WithElementRef<HTMLTextareaAttributes>> = $props();
</script>

<textarea
  class={cn(
		'cladd-cut cladd-hoverable cladd-focusable-input flex field-sizing-content min-h-16 w-full rounded-cladd-md px-2.5 py-1.5 text-cladd-xs leading-relaxed font-medium text-cladd-fg selection:bg-brand/30 placeholder:text-cladd-fg-softer disabled:cursor-not-allowed disabled:opacity-50',
		className
	)}
  data-slot={dataSlot}
  bind:this={ref}
  bind:value
  {...restProps}
></textarea>
