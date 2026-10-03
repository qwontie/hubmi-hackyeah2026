<script lang="ts">
  import XIcon from "@lucide/svelte/icons/x";
  import { Dialog as DialogPrimitive } from "bits-ui";
  import type { ComponentProps, Snippet } from "svelte";
  import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";
  import DialogPortal from "./dialog-portal.svelte";
  import * as Dialog from "./index.js";

  let {
    ref = $bindable(null),
    class: className,
    portalProps,
    children,
    showCloseButton = true,
    ...restProps
  }: WithoutChildrenOrChild<DialogPrimitive.ContentProps> & {
    portalProps?: WithoutChildrenOrChild<ComponentProps<typeof DialogPortal>>;
    children: Snippet;
    showCloseButton?: boolean;
  } = $props();
</script>

<DialogPortal {...portalProps}>
  <Dialog.Overlay />
  <DialogPrimitive.Content
    class={cn(
			'cladd-surface cladd-gradient cladd-outline cladd-level-1 cladd-anim-dialog fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-cladd-dialog p-4 text-cladd-fg shadow-cladd-popover outline-none sm:max-w-lg',
			className
		)}
    data-slot="dialog-content"
    bind:ref
    {...restProps}
  >
    {@render children?.()}
    {#if showCloseButton}
      <DialogPrimitive.Close
        class="cladd-ghost cladd-hoverable cladd-clickable cladd-focusable absolute end-3 top-3 flex size-cladd-md items-center justify-center rounded-full text-cladd-fg-soft disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4"
      >
        <XIcon />
        <span class="sr-only">Close</span>
      </DialogPrimitive.Close>
    {/if}
  </DialogPrimitive.Content>
</DialogPortal>
