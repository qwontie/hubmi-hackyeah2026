<script lang="ts">
  import { Avatar as AvatarPrimitive } from "bits-ui";
  import { cn } from "$lib/utils.js";

  let {
    ref = $bindable(null),
    loadingStatus = $bindable("loading"),
    class: className,
    ...restProps
  }: AvatarPrimitive.RootProps = $props();
</script>

<AvatarPrimitive.Root
  class={cn(
		'cladd-surface cladd-gradient cladd-outline relative flex size-cladd-lg shrink-0 overflow-hidden rounded-full',
		className
	)}
  data-slot="avatar"
  bind:loadingStatus
  bind:ref
  {...restProps}
/>
