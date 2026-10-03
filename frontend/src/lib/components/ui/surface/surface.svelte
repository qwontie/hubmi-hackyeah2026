<script lang="ts" module>
  import type { HTMLAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";
  import type { CladdColor } from "../button/button.svelte";

  export type SurfaceVariant =
    | "solid"
    | "gradient"
    | "solid-fill"
    | "gradient-fill"
    | "transparent";

  export type SurfaceProps = WithElementRef<HTMLAttributes<HTMLElement>> & {
    as?: string;
    variant?: SurfaceVariant;
    outline?: boolean;
    hoverable?: boolean;
    clickable?: boolean;
    level?: 1 | 2 | 3 | 4 | 5;
    color?: CladdColor;
  };
</script>

<script lang="ts">
  let {
    ref = $bindable(null),
    as = "div",
    variant = "solid",
    outline = false,
    hoverable = false,
    clickable = false,
    level,
    color,
    class: className,
    children,
    ...restProps
  }: SurfaceProps = $props();

  const variantClass: Record<SurfaceVariant, string> = {
    gradient: "cladd-surface cladd-gradient",
    "gradient-fill": "cladd-surface cladd-gradient-fill",
    solid: "cladd-surface",
    "solid-fill": "cladd-surface cladd-fill",
    transparent: "cladd-ghost",
  };
</script>

<!-- Nested surfaces step one level deeper automatically; `level` pins it. -->
<svelte:element
  class={cn(
		variantClass[variant],
		outline && 'cladd-outline',
		hoverable && 'cladd-hoverable',
		clickable && 'cladd-clickable',
		level && `cladd-level-${level}`,
		color && `cladd-color-${color}`,
		'text-cladd-fg',
		className
	)}
  data-slot="surface"
  this={as}
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</svelte:element>
