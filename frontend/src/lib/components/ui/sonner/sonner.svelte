<script lang="ts">
  import CircleCheckIcon from "@lucide/svelte/icons/circle-check";
  import InfoIcon from "@lucide/svelte/icons/info";
  import Loader2Icon from "@lucide/svelte/icons/loader-2";
  import OctagonXIcon from "@lucide/svelte/icons/octagon-x";
  import TriangleAlertIcon from "@lucide/svelte/icons/triangle-alert";
  import { mode } from "mode-watcher";
  import {
    Toaster as Sonner,
    type ToasterProps as SonnerProps,
  } from "svelte-sonner";

  let { ...restProps }: SonnerProps = $props();
</script>

<Sonner
  class="toaster group"
  style="--normal-bg: var(--color-popover); --normal-text: var(--color-popover-foreground); --normal-border: transparent; --border-radius: var(--radius-cladd-toast);"
  theme={mode.current}
  toastOptions={{
		classes: {
			toast:
				'cladd-surface cladd-gradient cladd-outline cladd-level-3 !rounded-cladd-toast !py-3 !ps-4 !pe-4 !gap-3 !shadow-cladd-popover !text-cladd-fg',
			title: '!text-cladd-sm !font-semibold',
			description: '!text-cladd-xs !leading-relaxed !text-cladd-fg-soft',
			actionButton:
				'cladd-surface cladd-gradient cladd-outline cladd-color-brand !rounded-full !bg-cladd-surface !text-cladd-primary !font-semibold',
			cancelButton: 'cladd-surface cladd-gradient !rounded-full !bg-cladd-surface !text-cladd-fg',
			closeButton:
				'cladd-surface cladd-gradient cladd-outline !bg-cladd-surface !text-cladd-fg-soft !border-0',
			success: '[&_[data-icon]]:text-success',
			error: '[&_[data-icon]]:text-destructive',
			warning: '[&_[data-icon]]:text-warning',
			info: '[&_[data-icon]]:text-brand'
		}
	}}
  {...restProps}
  >{#snippet loadingIcon()}
    <Loader2Icon class="size-4 animate-spin" />
  {/snippet}
  {#snippet successIcon()}
    <CircleCheckIcon class="size-4" />
  {/snippet}
  {#snippet errorIcon()}
    <OctagonXIcon class="size-4" />
  {/snippet}
  {#snippet infoIcon()}
    <InfoIcon class="size-4" />
  {/snippet}
  {#snippet warningIcon()}
    <TriangleAlertIcon class="size-4" />
  {/snippet}
</Sonner>
