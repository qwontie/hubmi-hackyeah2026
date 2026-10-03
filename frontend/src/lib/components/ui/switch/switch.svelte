<script lang="ts">
  import { Switch as SwitchPrimitive } from "bits-ui";
  import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    checked = $bindable(false),
    ...restProps
  }: WithoutChildrenOrChild<SwitchPrimitive.RootProps> = $props();
</script>

<SwitchPrimitive.Root
  class={cn(
		'peer group/switch cladd-surface cladd-outline cladd-focusable inline-flex h-cladd-md w-12 shrink-0 items-center rounded-full p-1 disabled:cursor-not-allowed disabled:opacity-50',
		className
	)}
  data-slot="switch"
  bind:checked
  bind:ref
  {...restProps}
>
  <SwitchPrimitive.Thumb data-slot="switch-thumb">
    {#snippet child({ props })}
      <span
        {...props}
        class={cn(
					'cladd-surface cladd-gradient cladd-outline cladd-fill-checked pointer-events-none relative block size-cladd-thumb-sm rounded-full transition-[translate,background-color,box-shadow] duration-300',
					checked ? 'cladd-color-brand translate-x-cladd-thumb-sm' : 'translate-x-0'
				)}
      >
        <!-- Two bars: a × while off, folding into a ✓ when on. -->
        <span
          class={cn(
						'absolute inset-0 transition-[rotate,scale] duration-300 group-active/switch:scale-90',
						checked && 'rotate-180'
					)}
        >
          <span
            class={cn(
							'absolute top-1/2 left-1/2 -mt-px -ml-2 h-0.5 w-4 rotate-45 rounded-full transition-[translate,scale,rotate,background-color] duration-300',
							checked
								? 'translate-x-0.5 translate-y-[-1.75px] scale-x-40 bg-cladd-on-primary'
								: 'scale-x-75 bg-cladd-fg-soft'
						)}
          ></span>
          <span
            class={cn(
							'absolute top-1/2 left-1/2 -mt-px -ml-2 h-0.5 w-4 -rotate-45 rounded-full transition-[translate,scale,rotate,background-color] duration-300',
							checked
								? 'translate-x-[-1.5px] scale-x-60 -rotate-60 bg-cladd-on-primary'
								: 'scale-x-75 bg-cladd-fg-soft'
						)}
          ></span>
        </span>
      </span>
    {/snippet}
  </SwitchPrimitive.Thumb>
</SwitchPrimitive.Root>
