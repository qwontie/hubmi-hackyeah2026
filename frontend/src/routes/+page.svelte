<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";

  $effect(() => {
    goto(resolve("/needs"), { replaceState: true });
  });
</script>

<svelte:head>
  <title>HubMi</title>
</svelte:head>
