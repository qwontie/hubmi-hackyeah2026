<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { session } from "$lib/auth/session.svelte";

  $effect(() => {
    goto(resolve(session.me?.role === "expert" ? "/expert" : "/needs"), {
      replaceState: true,
    });
  });
</script>

<svelte:head>
  <title>HubMi</title>
</svelte:head>
