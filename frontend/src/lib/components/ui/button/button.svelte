<script lang="ts" module>
  import type {
    HTMLAnchorAttributes,
    HTMLButtonAttributes,
  } from "svelte/elements";
  import { tv, type VariantProps } from "tailwind-variants";
  import { cn, type WithElementRef } from "$lib/utils.js";

  export type CladdColor =
    | "neutral"
    | "brand"
    | "red"
    | "pink"
    | "purple"
    | "blue"
    | "cyan"
    | "lime"
    | "green"
    | "yellow"
    | "orange";

  export const buttonVariants = tv({
    base: "cladd-clickable cladd-focusable relative inline-flex shrink-0 cursor-pointer select-none items-center justify-center gap-2 whitespace-nowrap font-semibold disabled:pointer-events-none disabled:*:opacity-40 aria-disabled:pointer-events-none aria-disabled:*:opacity-40 aria-invalid:outline-destructive [&_svg:not([class*='size-'])]:size-4 [&_svg]:pointer-events-none [&_svg]:shrink-0",
    compoundVariants: [{ class: "h-auto rounded-none px-0", variant: "link" }],
    defaultVariants: {
      rounded: false,
      size: "default",
      variant: "default",
    },
    variants: {
      rounded: {
        false: "",
        true: "rounded-full",
      },
      size: {
        default: "h-cladd-md rounded-cladd-md px-2.5 text-cladd-xs",
        icon: "size-cladd-md rounded-cladd-md",
        "icon-lg": "size-cladd-lg rounded-cladd-lg",
        "icon-sm": "size-cladd-sm rounded-cladd-sm",
        "icon-xs":
          "size-cladd-xs rounded-cladd-xs [&_svg:not([class*=size-])]:size-3",
        lg: "h-cladd-lg rounded-cladd-lg px-3 text-cladd-xs",
        sm: "h-cladd-sm gap-1.5 rounded-cladd-sm px-2.5 text-cladd-xs",
        xl: "h-cladd-xl rounded-cladd-xl px-3.5 text-cladd-sm",
        xs: "h-cladd-xs gap-1.5 rounded-cladd-xs px-2 text-cladd-xs [&_svg:not([class*=size-])]:size-3",
      },
      variant: {
        default:
          "cladd-surface cladd-gradient cladd-outline cladd-hoverable text-cladd-fg",
        destructive:
          "cladd-surface cladd-gradient cladd-outline cladd-hoverable cladd-color-red text-cladd-primary",
        fill: "cladd-surface cladd-gradient-fill cladd-outline cladd-hoverable",
        ghost: "cladd-ghost cladd-hoverable text-cladd-fg",
        link: "text-cladd-fg underline-offset-4 hover:underline",
        outline:
          "cladd-surface cladd-gradient cladd-outline cladd-hoverable text-cladd-fg",
        secondary: "cladd-surface cladd-gradient cladd-hoverable text-cladd-fg",
      },
    },
  });

  /** Swaps the variant's accent for an explicit one: `<Button color="green">`. */
  export function withColor(classes: string, color?: CladdColor) {
    if (!color) {
      return classes;
    }
    return `${classes.replace(/\bcladd-color-\w+/g, "")} cladd-color-${color}`;
  }

  export type ButtonVariant = VariantProps<typeof buttonVariants>["variant"];
  export type ButtonSize = VariantProps<typeof buttonVariants>["size"];

  export type ButtonProps = WithElementRef<HTMLButtonAttributes> &
    WithElementRef<HTMLAnchorAttributes> & {
      variant?: ButtonVariant;
      size?: ButtonSize;
      rounded?: boolean;
      color?: CladdColor;
    };
</script>

<script lang="ts">
  let {
    class: className,
    variant = "default",
    size = "default",
    rounded = false,
    color,
    ref = $bindable(null),
    href,
    type = "button",
    disabled,
    children,
    ...restProps
  }: ButtonProps = $props();

  const classes = $derived(
    cn(withColor(buttonVariants({ rounded, size, variant }), color), className)
  );
</script>

<!-- Content sits in its own box so the press can shrink it while the surface stays put. -->
{#if href}
  <a
    aria-disabled={disabled}
    class={classes}
    data-slot="button"
    href={disabled ? undefined : href}
    role={disabled ? 'link' : undefined}
    tabindex={disabled ? -1 : undefined}
    bind:this={ref}
    {...restProps}
  >
    <span class="cladd-button-content" data-slot="button-content"
      >{@render children?.()}</span
    >
  </a>
{:else}
  <button
    class={classes}
    data-slot="button"
    {disabled}
    {type}
    bind:this={ref}
    {...restProps}
  >
    <span class="cladd-button-content" data-slot="button-content"
      >{@render children?.()}</span
    >
  </button>
{/if}
