<script lang="ts" module>
  import { tv, type VariantProps } from "tailwind-variants";
  export const sheetVariants = tv({
    base: "cladd-surface cladd-gradient cladd-outline cladd-level-1 fixed z-50 flex flex-col gap-4 overflow-hidden text-cladd-fg shadow-cladd-popover outline-none ease-[cubic-bezier(0,1,0.2,1.1)] data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:duration-200 data-[state=open]:duration-500 data-[state=closed]:ease-in",
    defaultVariants: {
      side: "right",
    },
    variants: {
      side: {
        bottom:
          "data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom inset-x-2 bottom-2 h-auto rounded-cladd-panel",
        left: "data-[state=closed]:slide-out-to-start data-[state=open]:slide-in-from-start inset-y-2 start-2 w-3/4 rounded-cladd-panel sm:max-w-sm",
        right:
          "data-[state=closed]:slide-out-to-end data-[state=open]:slide-in-from-end inset-y-2 end-2 w-3/4 rounded-cladd-panel sm:max-w-sm",
        top: "data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top inset-x-2 top-2 h-auto rounded-cladd-panel",
      },
    },
  });

  export type Side = VariantProps<typeof sheetVariants>["side"];
</script>

<script lang="ts">
  import XIcon from "@lucide/svelte/icons/x";
  import { Dialog as SheetPrimitive } from "bits-ui";
  import type { ComponentProps, Snippet } from "svelte";
  import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";
  import SheetOverlay from "./sheet-overlay.svelte";
  import SheetPortal from "./sheet-portal.svelte";

  let {
    ref = $bindable(null),
    class: className,
    side = "right",
    portalProps,
    children,
    ...restProps
  }: WithoutChildrenOrChild<SheetPrimitive.ContentProps> & {
    portalProps?: WithoutChildrenOrChild<ComponentProps<typeof SheetPortal>>;
    side?: Side;
    children: Snippet;
  } = $props();
</script>

<SheetPortal {...portalProps}>
  <SheetOverlay />
  <SheetPrimitive.Content
    class={cn(sheetVariants({ side }), className)}
    data-slot="sheet-content"
    bind:ref
    {...restProps}
  >
    {@render children?.()}
    <SheetPrimitive.Close
      class="cladd-ghost cladd-hoverable cladd-clickable cladd-focusable absolute end-3 top-3 flex size-cladd-md items-center justify-center rounded-full text-cladd-fg-soft disabled:pointer-events-none"
    >
      <XIcon class="size-4" />
      <span class="sr-only">Close</span>
    </SheetPrimitive.Close>
  </SheetPrimitive.Content>
</SheetPortal>
