<script lang="ts">
  import type { AdminTestSignup, SignupStatus } from "$lib/api/admin";
  import { signupStatuses } from "$lib/opinions";

  let {
    signup,
    onstatus,
  }: {
    signup: AdminTestSignup;
    onstatus: (
      signup: AdminTestSignup,
      status: SignupStatus,
      anchor: HTMLElement | null
    ) => void;
  } = $props();
</script>

<fieldset class="seg">
  <legend class="sr-only">Stan zgłoszenia: {signup.innovation.title}</legend>
  {#each signupStatuses as st (st.id)}
    <button
      aria-pressed={signup.status === st.id}
      onclick={(event) => onstatus(signup, st.id, event.currentTarget)}
      type="button"
    >
      {st.label}
    </button>
  {/each}
</fieldset>

<style>
  .seg {
    display: inline-flex;
    gap: 2px;
    justify-self: start;
    padding: 3px;
    margin: 0;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .seg button {
    position: relative;
    height: 30px;
    padding: 0 11px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
    border-radius: 9px;
    transition:
      background-color 150ms ease,
      color 150ms ease;
  }

  .seg button:hover {
    color: var(--hm-ink);
  }

  .seg button[aria-pressed="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.6),
      transparent
    );
    box-shadow: var(--shadow-cladd-outline);
  }

  @media (max-width: 899px) {
    .seg button {
      height: 44px;
    }
  }
</style>
