<script lang="ts">
  import "./layout.css";
  import { ModeWatcher } from "mode-watcher";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { session } from "$lib/auth/session.svelte";
  import ErrorState from "$lib/components/error-state.svelte";
  import Shell from "$lib/components/hub/shell.svelte";

  let { children } = $props();

  const loginPath = resolve("/login");
  const bare = $derived(page.url.pathname === loginPath);
  const target = $derived(`${page.url.pathname}${page.url.search}`);

  $effect(() => {
    if (!(bare || session.loaded)) {
      session.load();
    }
  });

  $effect(() => {
    if (!bare && session.loaded && !session.error && session.me === null) {
      goto(`${loginPath}?next=${encodeURIComponent(target)}`, {
        replaceState: true,
      });
    }
  });
</script>

<ModeWatcher defaultMode="light" track={false} />

{#if bare}
  {@render children()}
{:else if session.me}
  <Shell>{@render children()}</Shell>
{:else if session.error}
  <main class="flex min-h-dvh items-center justify-center">
    <ErrorState error={session.error} retry={() => session.load()} />
  </main>
{/if}
