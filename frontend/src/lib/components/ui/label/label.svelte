<script lang="ts">
  import { Label as LabelPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: {
    ref?: any;
    class?: string;
    children?: any;
    [key: string]: any;
  } = $props();
</script>

<LabelPrimitive.Root
  class={cn(
		'text-cladd-xs leading-none font-medium text-cladd-fg-soft peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
		className
	)}
  bind:ref
  {...restProps}
>
  {@render children?.()}
</LabelPrimitive.Root>
