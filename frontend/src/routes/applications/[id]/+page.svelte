<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import { getApplication } from "$lib/api/admin";
  import ErrorState from "$lib/components/error-state.svelte";

  let loadError = $state<Error | null>(null);

  async function open(id: string) {
    loadError = null;
    try {
      const application = await getApplication(id);
      await goto(
        `${resolve("/grants/[[id]]", { id: application.call.id })}?app=${application.id}`,
        { replaceState: true }
      );
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    open(page.params.id ?? "");
  });
</script>

<svelte:head>
  <title>Wniosek · HubMi</title>
</svelte:head>

<main class="grid place-content-center p-10">
  {#if loadError}
    <ErrorState error={loadError} retry={() => open(page.params.id ?? "")} />
  {:else}
    <p class="text-hm-ink-soft text-sm">Wczytywanie…</p>
  {/if}
</main>
