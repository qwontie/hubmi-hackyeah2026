<script lang="ts" module>
  import { tv, type VariantProps } from "tailwind-variants";

  export const badgeVariants = tv({
    base: "cladd-surface inline-flex h-cladd-nested-md w-fit shrink-0 select-none items-center justify-center gap-1 overflow-hidden whitespace-nowrap rounded-cladd-sm px-2 font-semibold text-cladd-xs leading-none has-[>svg:first-child]:ps-1.5 has-[>svg:last-child]:pe-1.5 [&>svg]:pointer-events-none [&>svg]:size-3",
    defaultVariants: {
      variant: "default",
    },
    variants: {
      variant: {
        default:
          "cladd-gradient cladd-outline cladd-color-brand text-cladd-primary",
        destructive:
          "cladd-gradient cladd-outline cladd-color-red text-cladd-primary",
        fill: "cladd-gradient-fill cladd-outline cladd-color-brand",
        outline: "cladd-ghost text-cladd-fg shadow-cladd-outline",
        secondary: "cladd-gradient cladd-outline text-cladd-fg",
        success:
          "cladd-gradient cladd-outline cladd-color-green text-cladd-primary",
        warning:
          "cladd-gradient cladd-outline cladd-color-yellow text-cladd-primary",
      },
    },
  });

  export type BadgeVariant = VariantProps<typeof badgeVariants>["variant"];
</script>

<script lang="ts">
  import type { HTMLAnchorAttributes } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";
  import { type CladdColor, withColor } from "../button/button.svelte";

  let {
    ref = $bindable(null),
    href,
    class: className,
    variant = "default",
    color,
    children,
    ...restProps
  }: WithElementRef<HTMLAnchorAttributes> & {
    variant?: BadgeVariant;
    color?: CladdColor;
  } = $props();
</script>

<svelte:element
  class={cn(
		withColor(badgeVariants({ variant }), color),
		href && 'cladd-hoverable cladd-focusable',
		className
	)}
  data-slot="badge"
  {href}
  this={href ? 'a' : 'span'}
  bind:this={ref}
  {...restProps}
>
  {@render children?.()}
</svelte:element>
