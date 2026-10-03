<script lang="ts">
  import { onDestroy } from "svelte";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminFeedback,
    type AdminTestSignup,
    type FeedbackByInnovation,
    feedbackByInnovation,
    listComments,
    listSignups,
    type SignupStatus,
    setSignupStatus,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import { powiatName, when } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  const sorts = [
    { id: "recent", label: "Ostatnie" },
    { id: "does_not_fit", label: "Nie pasują" },
    { id: "testers", label: "Chętni do testów" },
  ];
  const who: Record<AdminTestSignup["who"], string> = {
    expert: "Ekspert lub ekspertka",
    local_government: "Samorząd",
    ngo: "Organizacja pozarządowa",
    resident: "Mieszkaniec lub mieszkanka",
  };
  const signupStatuses: { id: SignupStatus; label: string }[] = [
    { id: "new", label: "Nowe" },
    { id: "contacted", label: "Po kontakcie" },
    { id: "closed", label: "Zamknięte" },
  ];

  let rows = $state<FeedbackByInnovation[]>([]);
  let comments = $state<AdminFeedback[]>([]);
  let signups = $state<AdminTestSignup[]>([]);
  let loadError = $state<Error | null>(null);
  let loaded = $state(false);

  const sort = $derived(page.url.searchParams.get("sort") ?? "recent");

  async function load(s: string) {
    try {
      const [a, b, c] = await Promise.all([
        feedbackByInnovation(s),
        listComments(),
        listSignups(),
      ]);
      rows = a.items;
      comments = b.items.filter((f) => f.comment);
      signups = c.items;
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    } finally {
      loaded = true;
    }
  }

  $effect(() => {
    load(sort);
  });

  const offs = [
    live.on("feedback.created", () => load(sort)),
    live.on("test_signup.created", () => load(sort)),
  ];

  onDestroy(() => {
    for (const off of offs) {
      off();
    }
  });

  async function change(
    signup: AdminTestSignup,
    status: SignupStatus,
    event: MouseEvent
  ) {
    const button = event.currentTarget as HTMLElement;
    const before = signup.status;
    signup.status = status;
    try {
      Object.assign(signup, await setSignupStatus(signup.id, status));
      showTip(button, "Zapisano");
    } catch (e) {
      signup.status = before;
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
    }
  }

  const kindWord = {
    does_not_fit: "Nie pasuje",
    fits: "Pasuje",
    improvement: "Usprawnienie",
  };
</script>

<svelte:head>
  <title>Testerzy · HubMi</title>
</svelte:head>

<main class="board">
  <header>
    <h1
      class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
    >
      Testerzy
    </h1>
  </header>

  {#if loadError && !loaded}
    <ErrorState error={loadError} retry={() => load(sort)} />
  {:else if !loaded}
    <p class="text-hm-ink-soft text-sm">Wczytywanie…</p>
  {:else}
    <div class="cols">
      <section aria-labelledby="votes-h" class="panel">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 class="font-semibold text-sm" id="votes-h">Oceny innowacji</h2>
          <nav aria-label="Kolejność" class="filter">
            {#each sorts as s (s.id)}
              <a
                aria-current={s.id === sort ? "true" : undefined}
                data-sveltekit-noscroll
                data-sveltekit-replacestate
                href="{resolve('/testers')}?sort={s.id}"
                >{s.label}</a
              >
            {/each}
          </nav>
        </div>
        {#if rows.length === 0}
          <p class="text-hm-ink-soft text-sm">
            Nikt jeszcze nie ocenił żadnej innowacji.
          </p>
        {:else}
          <table>
            <thead>
              <tr>
                <th scope="col">Innowacja</th>
                <th class="n" scope="col">Pasuje</th>
                <th class="n" scope="col">Nie pasuje</th>
                <th class="n" scope="col">Usprawnienia</th>
                <th class="n" scope="col">Chętni</th>
              </tr>
            </thead>
            <tbody>
              {#each rows as r (r.innovation.slug)}
                <tr>
                  <th scope="row">
                    <a href="{resolve('/library')}/{r.innovation.slug}"
                      >{r.innovation.title}</a
                    >
                  </th>
                  <td class="n tabular">{r.fits}</td>
                  <td class={["n tabular", r.does_not_fit > r.fits && "warn"]}>
                    {r.does_not_fit}
                  </td>
                  <td class="n tabular">{r.improvements}</td>
                  <td class="n tabular">{r.testers}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

        {#if comments.length > 0}
          <h2 class="mt-6 mb-2 font-semibold text-sm">
            Komentarze i&nbsp;usprawnienia
          </h2>
          <ol class="list">
            {#each comments.slice(0, 20) as c (c.id)}
              <li>
                <span class="text-hm-ink-soft text-xs"
                  >{kindWord[c.kind]}
                  · {c.innovation.title} · {when(c.updated_at)}</span
                >
                <p class="text-sm">{c.comment}</p>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      <section aria-labelledby="sign-h" class="panel">
        <h2 class="mb-3 font-semibold text-sm" id="sign-h">
          Zgłoszenia do testów
        </h2>
        {#if signups.length === 0}
          <p class="text-hm-ink-soft text-sm">
            Nikt jeszcze nie zgłosił się do testów.
          </p>
        {:else}
          <ol class="list">
            {#each signups as s (s.id)}
              <li>
                <span class="font-semibold text-sm">{s.innovation.title}</span>
                <span class="text-hm-ink-soft text-xs">
                  {who[s.who]}{s.organization ? `, ${s.organization}` : ""}{s.powiat ? ` · ${powiatName(s.powiat, powiats.names)}` : ""}
                  · {when(s.created_at)}
                </span>
                {#if s.note}
                  <p class="text-sm">{s.note}</p>
                {/if}
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <a class="link text-sm" href="mailto:{s.contact_email}"
                    >{s.contact_email}</a
                  >
                  <fieldset class="seg">
                    <legend class="sr-only">Stan zgłoszenia</legend>
                    {#each signupStatuses as st (st.id)}
                      <button
                        aria-pressed={s.status === st.id}
                        onclick={(event) => change(s, st.id, event)}
                        type="button"
                      >
                        {st.label}
                      </button>
                    {/each}
                  </fieldset>
                </div>
              </li>
            {/each}
          </ol>
        {/if}
      </section>
    </div>
  {/if}
</main>

<style>
  .board {
    display: grid;
    gap: 18px;
    align-content: start;
    min-height: 0;
    padding: 24px 28px 28px;
    margin: 0 18px 18px;
    overflow: auto;
    background: var(--hm-board);
    border-radius: 26px;
    box-shadow: inset 1px 1px 0 oklch(1 0 0 / 0.8);
  }

  .cols {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
    gap: 14px;
    align-items: start;
  }

  .panel {
    min-width: 0;
    padding: 18px 20px;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: 0 0 0 1px var(--hm-rule);
  }

  .filter {
    display: inline-flex;
    gap: 2px;
    padding: 2px;
    background: var(--hm-sunk);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .filter a {
    display: inline-flex;
    align-items: center;
    height: 30px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    border-radius: 8px;
  }

  .filter a[aria-current="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  table {
    width: 100%;
    font-size: 13px;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 8px 6px;
    text-align: left;
    border-bottom: 1px solid var(--hm-rule);
  }

  thead th {
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  tbody th {
    font-weight: 600;
  }

  tbody th a:hover,
  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .n {
    width: 1%;
    text-align: right;
    white-space: nowrap;
  }

  .warn {
    font-weight: 600;
    color: var(--hm-bad);
  }

  .list {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .list li {
    display: grid;
    gap: 4px;
    padding: 10px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .list li:last-child {
    border-bottom: 0;
  }

  .seg {
    display: inline-flex;
    gap: 2px;
    padding: 2px;
    margin: 0;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .seg button {
    position: relative;
    height: 28px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
    border-radius: 8px;
  }

  .seg button[aria-pressed="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  @media (max-width: 899px) {
    .board {
      padding: 16px 12px;
      margin: 0 10px 10px;
      border-radius: 22px;
    }

    .cols {
      grid-template-columns: minmax(0, 1fr);
    }

    .panel {
      padding: 14px 12px;
    }

    th,
    td {
      padding: 8px 4px;
    }

    .seg button,
    .filter a {
      height: 40px;
    }
  }
</style>
