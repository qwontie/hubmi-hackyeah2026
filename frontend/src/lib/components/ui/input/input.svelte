<script lang="ts">
  import type {
    HTMLInputAttributes,
    HTMLInputTypeAttribute,
  } from "svelte/elements";
  import { cn, type WithElementRef } from "$lib/utils.js";

  type InputType = Exclude<HTMLInputTypeAttribute, "file">;

  type Props = WithElementRef<
    Omit<HTMLInputAttributes, "type"> &
      (
        | { type: "file"; files?: FileList }
        | { type?: InputType; files?: undefined }
      )
  >;

  let {
    ref = $bindable(null),
    value = $bindable(),
    type,
    files = $bindable(),
    class: className,
    "data-slot": dataSlot = "input",
    ...restProps
  }: Props = $props();
</script>

{#if type === 'file'}
  <input
    class={cn(
			'cladd-cut cladd-hoverable cladd-focusable-input flex h-cladd-md w-full min-w-0 rounded-cladd-md px-2.5 pt-1.5 text-cladd-xs font-medium text-cladd-fg selection:bg-brand/30 file:me-2 file:font-semibold file:text-cladd-fg placeholder:text-cladd-fg-softer disabled:cursor-not-allowed disabled:opacity-50',
			className
		)}
    data-slot={dataSlot}
    type="file"
    bind:this={ref}
    bind:files
    bind:value
    {...restProps}
  >
{:else}
  <input
    class={cn(
			'cladd-cut cladd-hoverable cladd-focusable-input flex h-cladd-md w-full min-w-0 rounded-cladd-md px-2.5 py-1 text-cladd-xs font-medium text-cladd-fg selection:bg-brand/30 placeholder:text-cladd-fg-softer disabled:cursor-not-allowed disabled:opacity-50',
			className
		)}
    data-slot={dataSlot}
    {type}
    bind:this={ref}
    bind:value
    {...restProps}
  >
{/if}
