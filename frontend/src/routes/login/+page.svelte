<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { login } from "$lib/api/auth";
  import { ApiError } from "$lib/api/client";
  import { session } from "$lib/auth/session.svelte";
  import RopsColophon from "$lib/components/hub/rops-colophon.svelte";
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

<main
  class="flex min-h-dvh flex-col items-center justify-center bg-hm-desk px-4 py-10"
>
  <form
    aria-describedby={failure ? "login-error" : undefined}
    class="sheet flex w-full max-w-[24rem] flex-col gap-5"
    onsubmit={submit}
  >
    <div class="flex items-center gap-3">
      <span aria-hidden="true" class="seal">Hm</span>
      <div>
        <h1 class="font-semibold text-hm-xl tracking-tight">HubMi</h1>
        <p class="text-balance text-hm-ink-soft text-hm-sm">
          Panel ROPS Kraków
        </p>
      </div>
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
      <button class="primary cladd-clickable" disabled={busy} type="submit">
        <span>{busy ? "Logowanie…" : "Zaloguj się"}</span>
      </button>
      {#if failure}
        <p class="text-hm-bad text-hm-sm" id="login-error" role="alert">
          {failure}
        </p>
      {/if}
    </div>
  </form>
  <RopsColophon variant="stack" />
</main>

<style>
  .sheet {
    padding: 28px;
    background: var(--hm-paper);
    border-radius: 24px;
    box-shadow: var(--hm-raised);
  }

  .seal {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    font-size: 15px;
    font-weight: 700;
    color: var(--hm-stamp);
    letter-spacing: -0.02em;
    background: var(--hm-paper);
    border-radius: 11px;
    box-shadow:
      inset 0 0 0 1.5px var(--hm-stamp),
      inset 0 0 0 3.5px var(--hm-paper),
      inset 0 0 0 4.5px var(--hm-stamp);
  }

  .primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 44px;
    font-size: 14px;
    font-weight: 600;
    color: var(--hm-on-stamp);
    background-color: var(--hm-stamp);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.16),
      transparent
    );
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-outline-fill);
    transition: background-color 150ms ease;
  }

  .primary:hover {
    background-color: var(--hm-stamp-press);
  }

  .primary:disabled {
    opacity: 0.6;
  }
</style>
