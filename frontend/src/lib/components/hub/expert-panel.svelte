<script lang="ts">
  import { tick, untrack } from "svelte";
  import {
    type Assignment,
    assignExpert,
    type Expert,
    forwardToExpert,
    listAssignments,
    listExperts,
    resendToExpert,
    unassign,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  let { kind, id }: { kind: "needs" | "ideas"; id: string } = $props();

  let assignments = $state<Assignment[]>([]);
  let experts = $state<Expert[]>([]);
  let open = $state(false);
  let chosen = $state("");
  let note = $state("");
  let email = $state("");
  let name = $state("");
  let expertise = $state("");
  let busy = $state(false);
  let failed = $state(false);

  const deliveryWords: Record<string, string> = {
    failed: "list nie dotarł",
    pending: "wysyłanie listu…",
    sent: "list wysłany",
    skipped: "bez listu, wysyłka wyłączona",
  };

  async function load(target: string) {
    try {
      const [a, e] = await Promise.all([
        listAssignments(kind, target),
        listExperts().catch(() => [] as Expert[]),
      ]);
      if (target === id) {
        assignments = a;
        experts = e;
        failed = false;
      }
    } catch {
      failed = true;
    }
  }

  $effect(() => {
    const target = id;
    untrack(() => {
      assignments = [];
      open = false;
      chosen = "";
      note = "";
      email = "";
      name = "";
      expertise = "";
      load(target);
    });
  });

  $effect(() => {
    const offs = [
      live.on("assignment.created", () => load(id)),
      live.on("assignment.answered", () => load(id)),
    ];
    return () => {
      for (const off of offs) {
        off();
      }
    };
  });

  const free = $derived(
    experts.filter((e) => !assignments.some((a) => a.expert.id === e.id))
  );

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const button = document.getElementById("assign-expert");
    if (!chosen || busy) {
      showTip(button, "Wybierz eksperta", "bad");
      return;
    }
    if (chosen === "email" && !email.trim()) {
      showTip(button, "Podaj adres e-mail eksperta", "bad");
      return;
    }
    busy = true;
    try {
      const a =
        chosen === "email"
          ? await forwardToExpert(kind, id, {
              email: email.trim(),
              expertise: expertise.trim() || null,
              name: name.trim() || null,
              note: note.trim() || null,
            })
          : await assignExpert(kind, id, chosen, note.trim());
      assignments = [...assignments, a];
      open = false;
      chosen = "";
      note = "";
      email = "";
      name = "";
      expertise = "";
      showTip(button, chosen === "email" ? "List wysłany" : "Prośba wysłana");
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się.",
        "bad"
      );
    } finally {
      busy = false;
    }
  }

  async function resend(a: Assignment, event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    try {
      const next = await resendToExpert(a.id);
      assignments = assignments.map((x) => (x.id === a.id ? next : x));
      showTip(button, "Wysłano ponownie");
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się.",
        "bad"
      );
    }
  }

  async function remove(a: Assignment, event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    try {
      await unassign(a.id);
      assignments = assignments.filter((x) => x.id !== a.id);
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się.",
        "bad"
      );
    }
  }
</script>

{#if !failed}
  <section aria-labelledby="expert-h-{id}" class="grid gap-2">
    <div class="flex items-center justify-between gap-3">
      <h3 class="font-semibold text-[13px]" id="expert-h-{id}">
        Opinia eksperta
      </h3>
      {#if !open}
        <button
          class="ghost cladd-clickable"
          id="ask-expert-{id}"
          onclick={async () => {
            open = true;
            await tick();
            document
              .querySelector<HTMLInputElement>(`input[name="expert-${id}"]`)
              ?.focus();
          }}
          type="button"
        >
          <span>Poproś eksperta</span>
        </button>
      {/if}
    </div>

    {#if assignments.length > 0}
      <ul class="list">
        {#each assignments as a (a.id)}
          <li>
            <span class="flex items-baseline justify-between gap-3">
              <span class="flex flex-wrap gap-x-1.5 text-sm">
                <b class="font-semibold">{a.expert.display_name}</b>
                {#if a.expert.expertise}
                  <span class="text-hm-ink-soft">{a.expert.expertise}</span>
                {/if}
                {#if a.expert.email}
                  <span class="text-hm-ink-soft">{a.expert.email}</span>
                {/if}
              </span>
              <span class={["st", a.status === "answered" && "ok"]}
                >{a.status === "answered" ? "Opinia wydana" : "Czeka na opinię"}</span
              >
            </span>
            <span class="text-hm-ink-soft text-xs">
              Kto prosił: {a.assigned_by} ·
              {when(a.created_at)}{a.note ? ` · „${a.note}”` : ""}{a.expert.email && a.delivery_status ? ` · ${deliveryWords[a.delivery_status] ?? a.delivery_status}` : ""}
            </span>
            {#each a.private_notes ?? [] as n (n.id)}
              <p class="pnote text-sm">
                <b class="font-semibold">Notatka dla ROPS:</b> {n.body}
              </p>
            {/each}
            {#if a.status === "open"}
              <span class="flex flex-wrap gap-3">
                <button
                  class="link relative justify-self-start text-xs"
                  onclick={(event) => remove(a, event)}
                  type="button"
                >
                  Cofnij prośbę
                </button>
                {#if a.expert.email}
                  <button
                    class="link relative justify-self-start text-xs"
                    onclick={(event) => resend(a, event)}
                    type="button"
                  >
                    Wyślij list ponownie
                  </button>
                {/if}
              </span>
            {/if}
          </li>
        {/each}
      </ul>
    {/if}

    {#if open}
      <form class="ask" onsubmit={submit}>
        <fieldset class="m-0 grid gap-1.5 border-0 p-0">
          <legend class="mb-1.5 font-semibold text-[13px]">
            Kogo poprosić
          </legend>
          {#each free as e (e.id)}
            <label class="pick">
              <input
                name="expert-{id}"
                type="radio"
                value={e.id}
                bind:group={chosen}
              >
              <span class="flex flex-wrap gap-x-1.5">
                <b class="font-semibold">{e.display_name}</b>
                {#if e.expertise}
                  <span class="text-hm-ink-soft">{e.expertise}</span>
                {/if}
              </span>
              <span class="text-hm-ink-soft text-xs tabular"
                >{e.open}
                w&nbsp;toku</span
              >
            </label>
          {/each}
          <label class="pick">
            <input
              name="expert-{id}"
              type="radio"
              value="email"
              bind:group={chosen}
            >
            <span class="flex flex-wrap gap-x-1.5">
              <b class="font-semibold">Ekspert bez konta, przez e-mail</b>
              <span class="text-hm-ink-soft"
                >dostanie list z&nbsp;osobistym linkiem do odpowiedzi</span
              >
            </span>
          </label>
        </fieldset>
        {#if chosen === "email"}
          <div class="grid gap-2 min-[900px]:grid-cols-3">
            <label class="grid gap-1 font-semibold text-[13px]">
              Adres e-mail
              <input
                class="well h-9 font-normal"
                inputmode="email"
                required
                type="email"
                bind:value={email}
              >
            </label>
            <label class="grid gap-1 font-semibold text-[13px]">
              Imię i nazwisko
              <input
                class="well h-9 font-normal"
                maxlength="200"
                bind:value={name}
              >
            </label>
            <label class="grid gap-1 font-semibold text-[13px]">
              Dziedzina
              <input
                class="well h-9 font-normal"
                maxlength="200"
                bind:value={expertise}
              >
            </label>
          </div>
        {/if}
        <label class="font-semibold text-[13px]" for="assign-note-{id}"
          >Prośba do eksperta</label
        >
        <textarea
          class="well"
          id="assign-note-{id}"
          maxlength="1000"
          rows="2"
          bind:value={note}
        ></textarea>
        <span class="flex items-center justify-end gap-2">
          <button
            class="ghost cladd-clickable"
            onclick={async () => {
              open = false;
              await tick();
              document.getElementById(`ask-expert-${id}`)?.focus();
            }}
            type="button"
          >
            <span>Anuluj</span>
          </button>
          <button
            class="primary cladd-clickable"
            disabled={busy}
            id="assign-expert"
            type="submit"
          >
            <span>{chosen === "email" ? "Wyślij list" : "Wyślij prośbę"}</span>
          </button>
        </span>
      </form>
    {/if}
  </section>
{/if}

<style>
  .list {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .list li {
    display: grid;
    gap: 4px;
    padding: 10px 0;
    border-bottom: 1px dashed var(--hm-rule);
  }

  .list li:last-child {
    border-bottom: 0;
  }

  .pnote {
    padding: 8px 10px;
    background: var(--hm-sunk);
    border-radius: 10px;
  }

  .st {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-stamp);
    white-space: nowrap;
  }

  .st::before {
    width: 6px;
    height: 6px;
    content: "";
    background: currentColor;
    border-radius: 50%;
  }

  .st.ok {
    color: var(--hm-ok);
  }

  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .ask {
    display: grid;
    gap: 8px;
    padding: 14px;
    background: var(--hm-board);
    border-radius: 14px;
    box-shadow: 0 0 0 1px var(--hm-rule);
  }

  .pick {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    min-height: 40px;
    padding: 6px 10px;
    font-size: 14px;
    cursor: pointer;
    border-radius: 10px;
  }

  .pick:hover {
    background: var(--hm-stamp-wash);
  }

  .pick:has(input:checked) {
    background: var(--hm-stamp-wash);
    box-shadow: inset 0 0 0 1.5px var(--hm-stamp);
  }

  .pick input {
    width: 16px;
    height: 16px;
    accent-color: var(--hm-stamp);
  }

  .well {
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 14px;
    line-height: 1.5;
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-cut-outline);
    outline: none;
    resize: vertical;
    field-sizing: content;
  }

  .well:focus {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .primary,
  .ghost {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    border-radius: 10px;
  }

  .primary {
    color: var(--hm-on-stamp);
    background-color: var(--hm-stamp);
    box-shadow: var(--shadow-cladd-outline-fill);
  }

  .primary:hover {
    background-color: var(--hm-stamp-press);
  }

  .ghost {
    color: var(--hm-ink);
    background: var(--hm-sunk);
    box-shadow: var(--shadow-cladd-outline);
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  @media (max-width: 899px) {
    .primary,
    .ghost {
      height: 44px;
    }
  }
</style>
