<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { login } from "$lib/api/auth";
  import { ApiError } from "$lib/api/client";
  import { session } from "$lib/auth/session.svelte";
  import { Button } from "$lib/components/ui/button";
  import { Input } from "$lib/components/ui/input";
  import { Label } from "$lib/components/ui/label";

  let user = $state("");
  let password = $state("");
  let busy = $state(false);
  let failure = $state<string | null>(null);

  const home = resolve("/");
  const next = $derived.by(() => {
    const raw = page.url.searchParams.get("next") ?? home;
    return raw.startsWith(home) && !raw.startsWith("//") ? raw : home;
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (busy) {
      return;
    }
    busy = true;
    failure = null;
    try {
      session.set(await login(user.trim(), password));
      await goto(next, { replaceState: true });
    } catch (e) {
      if (e instanceof ApiError) {
        failure =
          e.status === 401 || e.status === 422
            ? "Nieprawidłowy login lub hasło."
            : e.message;
      } else {
        failure = "Brak połączenia z serwerem.";
      }
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head>
  <title>Logowanie · HubMi</title>
</svelte:head>

<main class="flex min-h-dvh items-center justify-center px-6 py-10">
  <form
    aria-describedby={failure ? "login-error" : undefined}
    class="flex w-full max-w-[22rem] flex-col gap-5"
    onsubmit={submit}
  >
    <div class="flex flex-col gap-1">
      <h1 class="font-semibold text-hm-2xl tracking-tight">HubMi</h1>
      <p class="text-balance text-cladd-fg-soft text-hm-sm">
        Panel administracyjny Małopolskiego Hubu Innowacji Społecznych
      </p>
    </div>
    <div class="flex flex-col gap-1.5">
      <Label class="text-hm-sm" for="login">Login</Label>
      <Input
        autocapitalize="off"
        autocomplete="username"
        autocorrect="off"
        class="h-11 text-hm-base"
        id="login"
        name="login"
        required
        spellcheck="false"
        bind:value={user}
      />
    </div>
    <div class="flex flex-col gap-1.5">
      <Label class="text-hm-sm" for="password">Hasło</Label>
      <Input
        autocomplete="current-password"
        class="h-11 text-hm-base"
        id="password"
        name="password"
        required
        type="password"
        bind:value={password}
      />
    </div>
    <div class="flex flex-col gap-2">
      <Button
        class="h-11 text-hm-sm"
        disabled={busy}
        size="lg"
        type="submit"
        variant="fill"
      >
        {busy ? "Logowanie…" : "Zaloguj się"}
      </Button>
      {#if failure}
        <p class="text-bad text-hm-sm" id="login-error" role="alert">
          {failure}
        </p>
      {/if}
    </div>
  </form>
</main>
