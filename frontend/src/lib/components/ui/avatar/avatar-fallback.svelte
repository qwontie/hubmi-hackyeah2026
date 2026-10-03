<script lang="ts">
  import { Avatar as AvatarPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    class: className,
    ...restProps
  }: AvatarPrimitive.FallbackProps = $props();
</script>

<AvatarPrimitive.Fallback
  class={cn(
		'flex size-full items-center justify-center rounded-full text-cladd-xs font-semibold text-cladd-fg-soft uppercase',
		className
	)}
  data-slot="avatar-fallback"
  bind:ref
  {...restProps}
/>
