<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { logout } from "$lib/api/auth";
  import { session } from "$lib/auth/session.svelte";
  import { Button } from "$lib/components/ui/button";

  let busy = $state(false);

  async function signOut() {
    busy = true;
    try {
      await logout();
      session.set(null);
      await goto(resolve("/login"), { replaceState: true });
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head>
  <title>Panel administracyjny · HubMi</title>
</svelte:head>

<main
  class="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center"
>
  <h1 class="font-semibold text-hm-2xl tracking-tight">HubMi</h1>
  <p class="text-cladd-fg-soft text-hm-base">
    Zalogowano jako <strong class="text-cladd-fg">{session.me?.login}</strong>
  </p>
  <Button class="h-11" disabled={busy} onclick={signOut} variant="outline">
    Wyloguj się
  </Button>
</main>
