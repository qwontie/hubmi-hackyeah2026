<script lang="ts">
  import type { Component } from "svelte";
  import { Button } from "$lib/components/ui/button";
  import { cn } from "$lib/utils";

  let {
    title,
    icon: Icon,
    action,
    compact = false,
    class: className,
  }: {
    title: string;
    icon?: Component<{ class?: string; "aria-hidden"?: boolean | "true" }>;
    action?: { label: string; href?: string; onclick?: () => void };
    compact?: boolean;
    class?: string;
  } = $props();
</script>

<div
  class={cn(
    "flex flex-col items-center justify-center gap-3 text-center",
    compact ? "px-4 py-6" : "px-6 py-12",
    className
  )}
>
  <p class="flex items-center gap-2 text-cladd-fg-soft">
    {#if Icon}
      <Icon aria-hidden="true" class="size-4" />
    {/if}
    {title}
  </p>
  {#if action}
    <Button
      class="h-10 md:h-cladd-sm"
      href={action.href}
      onclick={action.onclick}
      size="sm"
      variant="outline"
    >
      {action.label}
    </Button>
  {/if}
</div>
