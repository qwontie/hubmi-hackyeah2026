<script lang="ts">
  import type { HTMLAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: WithElementRef<HTMLAttributes<HTMLSpanElement>> = $props();
</script>

<span
  class={cn('ms-auto font-mono text-cladd-2xs tracking-widest text-cladd-fg-softer', className)}
  data-slot="dropdown-menu-shortcut"
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</span>
