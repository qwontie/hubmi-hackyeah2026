<script lang="ts">
  import CheckIcon from "@lucide/svelte/icons/check";
  import MinusIcon from "@lucide/svelte/icons/minus";
  import { Checkbox as CheckboxPrimitive } from "bits-ui";
  import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    checked = $bindable(false),
    indeterminate = $bindable(false),
    class: className,
    ...restProps
  }: WithoutChildrenOrChild<CheckboxPrimitive.RootProps> = $props();
</script>

<CheckboxPrimitive.Root
  class={cn(
		'peer group/checkbox cladd-surface cladd-gradient cladd-outline cladd-hoverable cladd-clickable cladd-focusable relative flex size-cladd-thumb-sm shrink-0 items-center justify-center rounded-full text-cladd-fg-soft disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:outline-destructive',
		'cladd-fill-checked',
		(checked || indeterminate) && 'cladd-color-brand',
		className
	)}
  data-slot="checkbox"
  bind:checked
  bind:indeterminate
  bind:ref
  {...restProps}
>
  {#snippet children({ checked, indeterminate })}
    <span
      class={cn(
				'flex items-center justify-center transition-[scale,color] duration-200',
				checked || indeterminate
					? 'text-cladd-on-primary group-active/checkbox:scale-90'
					: 'scale-75 group-active/checkbox:scale-65'
			)}
      data-slot="checkbox-indicator"
    >
      {#if indeterminate}
        <MinusIcon class="size-3" strokeWidth={3} />
      {:else}
        <CheckIcon class="size-3" strokeWidth={3} />
      {/if}
    </span>
  {/snippet}
</CheckboxPrimitive.Root>
