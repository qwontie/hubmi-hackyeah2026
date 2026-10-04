<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminChallenge,
    listChallenges,
    patchChallenge,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import { when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  let challenges = $state<AdminChallenge[] | null>(null);
  let loadError = $state<Error | null>(null);
  let saving = $state(false);
  let editing = $state(false);
  let title = $state("");
  let summary = $state("");
  let description = $state("");

  const unchecked = $derived(
    page.url.searchParams.get("wyzwania") === "do-sprawdzenia"
  );
  const openSlug = $derived(page.url.searchParams.get("wyzwanie"));

  function href(next: { unchecked?: boolean; open?: string | null }) {
    const params = new URLSearchParams(page.url.searchParams);
    const u = next.unchecked ?? unchecked;
    const o = next.open === undefined ? openSlug : next.open;
    if (u) {
      params.set("wyzwania", "do-sprawdzenia");
    } else {
      params.delete("wyzwania");
    }
    if (o) {
      params.set("wyzwanie", o);
    } else {
      params.delete("wyzwanie");
    }
    const q = params.toString();
    return `${resolve("/stats")}${q ? `?${q}` : ""}`;
  }

  async function load() {
    try {
      challenges = await listChallenges();
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    load();
  });

  $effect(() =>
    live.on("challenge.updated", (data) => {
      const next = data as AdminChallenge;
      challenges =
        challenges?.map((c) => (c.id === next.id ? { ...c, ...next } : c)) ??
        null;
    })
  );

  $effect(() =>
    live.on("knowledge.import.finished", () => {
      load();
    })
  );

  const waiting = $derived(
    (challenges ?? []).filter((c) => !c.verified).length
  );

  const groups = $derived.by(() => {
    const byArea = new Map<string, { name: string; items: AdminChallenge[] }>();
    for (const c of challenges ?? []) {
      if (unchecked && c.verified) {
        continue;
      }
      const group = byArea.get(c.area.slug) ?? {
        items: [],
        name: c.area.name,
      };
      group.items.push(c);
      byArea.set(c.area.slug, group);
    }
    return [...byArea.entries()]
      .map(([slug, g]) => ({ slug, ...g }))
      .sort((a, b) => b.items.length - a.items.length);
  });

  function toggle(c: AdminChallenge) {
    editing = false;
    goto(href({ open: openSlug === c.slug ? null : c.slug }), {
      keepFocus: true,
      noScroll: true,
      replaceState: true,
    });
  }

  function startEdit(c: AdminChallenge) {
    ({ description, summary, title } = c);
    editing = true;
  }

  function replace(next: AdminChallenge) {
    challenges = challenges?.map((c) => (c.id === next.id ? next : c)) ?? null;
  }

  async function run(
    c: AdminChallenge,
    body: Record<string, unknown>,
    button: HTMLElement | null,
    done: string
  ) {
    saving = true;
    try {
      replace(await patchChallenge(c.id, body));
      showTip(button, done);
      return true;
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
      return false;
    } finally {
      saving = false;
    }
  }

  async function save(event: SubmitEvent, c: AdminChallenge) {
    event.preventDefault();
    const button = (event.currentTarget as HTMLFormElement).querySelector(
      "button[type=submit]"
    ) as HTMLElement | null;
    const body: Record<string, string> = {};
    if (title.trim() !== c.title) {
      body.title = title.trim();
    }
    if (summary.trim() !== c.summary.trim()) {
      body.summary = summary.trim();
    }
    if (description.trim() !== c.description.trim()) {
      body.description = description.trim();
    }
    if (Object.keys(body).length === 0) {
      editing = false;
      return;
    }
    if (await run(c, body, button, "Zapisano")) {
      editing = false;
    }
  }

  const scopeWords = (scope: string) =>
    scope === "Polska" ? "dane dla całej Polski" : scope;
</script>

<section aria-labelledby="ch-h" class="panel">
  <header class="phead">
    <h2 class="h" id="ch-h">
      Wyzwania regionu <span class="win">z&nbsp;dokumentów ROPS</span>
    </h2>
    {#if challenges && challenges.length > 0}
      <nav aria-label="Filtr wyzwań" class="filter">
        <a
          aria-current={unchecked ? undefined : "true"}
          data-sveltekit-noscroll
          data-sveltekit-replacestate
          href={href({ unchecked: false })}
          >Wszystkie <span class="tabular">{challenges.length}</span></a
        >
        <a
          aria-current={unchecked ? "true" : undefined}
          data-sveltekit-noscroll
          data-sveltekit-replacestate
          href={href({ unchecked: true })}
          >Do sprawdzenia <span class="tabular">{waiting}</span></a
        >
      </nav>
    {/if}
  </header>

  {#if loadError && !challenges}
    <ErrorState error={loadError} retry={load} />
  {:else if !challenges}
    <p class="empty">Wczytywanie…</p>
  {:else if challenges.length === 0}
    <p class="empty">
      Nie ma jeszcze wyzwań. Powstają z&nbsp;dokumentów ROPS:
      <a class="link" href={resolve("/materials/[[id]]", {})}
        >pobierz je w&nbsp;Materiałach</a
      >.
    </p>
  {:else if groups.length === 0}
    <p class="empty">Wszystkie wyzwania są sprawdzone.</p>
  {:else}
    <div class="areas">
      {#each groups as g (g.slug)}
        <section aria-labelledby="area-{g.slug}" class="area">
          <h3 class="ah" id="area-{g.slug}">
            {g.name} <span class="tabular">{g.items.length}</span>
          </h3>
          <ul class="rows">
            {#each g.items as c (c.id)}
              {@const open = openSlug === c.slug}
              <li class={["item", open && "open"]}>
                <button
                  aria-controls="ch-{c.id}"
                  aria-expanded={open}
                  class="row"
                  onclick={() => toggle(c)}
                  type="button"
                >
                  <span class="grid min-w-0 gap-[3px]">
                    <span class="font-semibold text-sm">{c.title}</span>
                    {#if c.figures.length > 0 || c.status !== "published"}
                      <span class="meta"
                        >{[c.status === "published" ? "" : "ukryte", c.figures[0] ? `${c.figures[0].value} ${c.figures[0].label}` : ""].filter(Boolean).join(" · ")}</span
                      >
                    {/if}
                  </span>
                  <span class={["st", c.verified && "ok"]}
                    >{c.verified ? "Sprawdzone" : "Do sprawdzenia"}</span
                  >
                </button>
                {#if open}
                  <div class="body" id="ch-{c.id}">
                    {#if editing}
                      <form class="grid gap-3" onsubmit={(e) => save(e, c)}>
                        <label class="grid gap-1.5">
                          <span class="font-semibold text-[13px]">Tytuł</span>
                          <textarea
                            class="well"
                            required
                            rows="1"
                            bind:value={title}
                          ></textarea>
                        </label>
                        <label class="grid gap-1.5">
                          <span class="font-semibold text-[13px]"
                            >W&nbsp;jednym zdaniu</span
                          >
                          <textarea
                            class="well"
                            rows="2"
                            bind:value={summary}
                          ></textarea>
                        </label>
                        <label class="grid gap-1.5">
                          <span class="font-semibold text-[13px]">Opis</span>
                          <textarea
                            class="well"
                            rows="5"
                            bind:value={description}
                          ></textarea>
                        </label>
                        <span class="actions">
                          <button
                            class="primary cladd-clickable"
                            disabled={saving}
                            type="submit"
                          >
                            <span>Zapisz</span>
                          </button>
                          <button
                            class="ghost cladd-clickable"
                            onclick={() => {
                              editing = false;
                            }}
                            type="button"
                          >
                            <span>Anuluj</span>
                          </button>
                        </span>
                      </form>
                    {:else}
                      <p class="text-sm">{c.summary}</p>
                      {#if c.description && c.description !== c.summary}
                        <p class="text-[13px] text-hm-ink-soft">
                          {c.description}
                        </p>
                      {/if}
                      {#if c.figures.length > 0}
                        <ul class="figs">
                          {#each c.figures as f, i (i)}
                            <li>
                              <span class="tabular font-semibold text-base"
                                >{f.value}</span
                              >
                              <span class="text-[13px]"
                                >{f.label}{f.year ? `, ${f.year}` : ""}
                                ({scopeWords(f.scope)})</span
                              >
                              <a
                                class="link text-xs"
                                href="{f.document_url}#page={f.page}"
                                rel="noopener"
                                target="_blank"
                                >{f.document_title}, s. {f.page}</a
                              >
                            </li>
                          {/each}
                        </ul>
                      {/if}
                      <p class="text-[13px] text-hm-ink-soft">
                        {#if c.verified}
                          Sprawdzone przez
                          {c.verified_by ?? "ROPS"}{c.verified_at ? ` ${when(c.verified_at)}` : ""}.
                        {:else}
                          Opracowanie automatyczne, jeszcze niesprawdzone.
                        {/if}
                      </p>
                      <p class="text-[13px]">
                        <a
                          class="link"
                          href="{c.source.url}{c.source.pages[0] ? `#page=${c.source.pages[0]}` : ''}"
                          rel="noopener"
                          target="_blank"
                          >Źródło:
                          {c.source.title}{c.source.pages.length ? `, s. ${c.source.pages.join(", ")}` : ""}</a
                        >
                      </p>
                      <span class="actions">
                        <button
                          class={[c.verified ? "ghost" : "primary", "cladd-clickable"]}
                          disabled={saving}
                          onclick={(event) =>
                            run(c, { verified: !c.verified }, event.currentTarget, c.verified ? "Cofnięto" : "Sprawdzone")}
                          type="button"
                        >
                          <span
                            >{c.verified ? "Cofnij sprawdzenie" : "Oznacz jako sprawdzone"}</span
                          >
                        </button>
                        <button
                          class="ghost cladd-clickable"
                          disabled={saving}
                          onclick={() => startEdit(c)}
                          type="button"
                        >
                          <span>Popraw tekst</span>
                        </button>
                        <button
                          class="ghost cladd-clickable"
                          disabled={saving}
                          onclick={(event) =>
                            run(c, { status: c.status === "published" ? "draft" : "published" }, event.currentTarget, c.status === "published" ? "Ukryto" : "Opublikowano")}
                          type="button"
                        >
                          <span
                            >{c.status === "published" ? "Ukryj" : "Opublikuj"}</span
                          >
                        </button>
                      </span>
                    {/if}
                  </div>
                {/if}
              </li>
            {/each}
          </ul>
        </section>
      {/each}
    </div>
  {/if}
</section>

<style>
  .panel {
    min-width: 0;
    padding: 18px 20px;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: 0 0 0 1px var(--hm-rule);
  }

  .phead {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .h {
    font-size: 14px;
    font-weight: 650;
  }

  .win {
    font-weight: 500;
    color: var(--hm-ink-soft);
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
    gap: 6px;
    align-items: center;
    height: 30px;
    padding: 0 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
    border-radius: 8px;
  }

  .filter a[aria-current="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  .areas {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px 28px;
    align-items: start;
  }

  .ah {
    display: flex;
    justify-content: space-between;
    padding: 10px 0 6px;
    font-size: 13px;
    font-weight: 600;
    border-bottom: 1px solid var(--hm-rule);
  }

  .ah span {
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .rows {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .item {
    border-bottom: 1px solid var(--hm-rule);
  }

  .item:last-child {
    border-bottom: 0;
  }

  .row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: baseline;
    width: 100%;
    padding: 9px 8px;
    text-align: left;
    border-radius: 10px;
    transition: background-color 150ms ease;
  }

  .row:hover {
    background: color-mix(in oklab, var(--hm-stamp) 5%, transparent);
  }

  .open .row {
    background: var(--hm-stamp-wash);
  }

  .body {
    display: grid;
    gap: 10px;
    padding: 10px 8px 14px;
  }

  .meta {
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 12px;
    color: var(--hm-ink-soft);
    white-space: nowrap;
  }

  .figs {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .figs li {
    display: grid;
    gap: 2px;
    padding: 8px 0;
    border-bottom: 1px dashed var(--hm-rule);
  }

  .figs li:last-child {
    border-bottom: 0;
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

  .empty {
    font-size: 13px;
    color: var(--hm-ink-soft);
  }

  .well {
    width: 100%;
    padding: 8px 10px;
    font-size: 14px;
    line-height: 1.45;
    resize: vertical;
    field-sizing: content;
    outline: none;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .well:focus {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .primary,
  .ghost {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 34px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    border-radius: 10px;
    transition: background-color 150ms ease;
  }

  .primary {
    color: var(--hm-on-stamp);
    background-color: var(--hm-stamp);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.16),
      transparent
    );
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

  .primary:disabled,
  .ghost:disabled {
    opacity: 0.6;
  }

  @media (max-width: 1180px) {
    .areas {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 899px) {
    .areas {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 899px), (pointer: coarse) {
    .row {
      min-height: 44px;
    }

    .primary,
    .ghost,
    .filter a {
      height: 44px;
    }
  }
</style>
