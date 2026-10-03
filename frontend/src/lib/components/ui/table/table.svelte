<script lang="ts">
  import type { HTMLTableAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    children,
    ...restProps
  }: WithElementRef<HTMLTableAttributes> = $props();
</script>

<div class="relative" data-slot="table-container">
  <table
    class={cn('w-full caption-bottom text-cladd-sm', className)}
    data-slot="table"
    bind:this={ref}
    {...restProps}
  >
    {@render children?.()}
  </table>
</div>
