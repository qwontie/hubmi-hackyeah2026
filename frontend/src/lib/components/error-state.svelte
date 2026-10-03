<script lang="ts">
  import { ApiError } from "$lib/api/client";
  import { Button } from "$lib/components/ui/button";
  import { cn } from "$lib/utils";

  let {
    error,
    retry,
    class: className,
  }: {
    error: Error | null;
    retry?: () => void;
    class?: string;
  } = $props();

  const title = $derived.by(() => {
    if (error instanceof ApiError) {
      if (error.status === 403) {
        return "Brak dostępu.";
      }
      if (error.status === 404) {
        return "Nie znaleziono.";
      }
      if (error.status >= 500) {
        return "Serwer zwrócił błąd. Spróbuj ponownie za chwilę.";
      }
      return error.message;
    }
    return "Brak połączenia z serwerem.";
  });
</script>

<div
  class={cn("flex flex-col items-center justify-center gap-3 px-6 py-12 text-center", className)}
>
  <p class="text-cladd-fg-soft">{title}</p>
  {#if retry}
    <Button onclick={retry} size="sm" variant="outline"
      >Spróbuj ponownie</Button
    >
  {/if}
</div>
