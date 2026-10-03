<script lang="ts">
  import { onDestroy } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminInnovation,
    type Category,
    type ImportProgress,
    type ImportRun,
    listAllInnovations,
    listCategories,
    listImportRuns,
    runImport,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import InnovationSheet from "$lib/components/hub/innovation-sheet.svelte";
  import MaterialIntake from "$lib/components/hub/material-intake.svelte";
  import type { FolderTab } from "$lib/components/hub/types";
  import { plural, when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  let items = $state<AdminInnovation[]>([]);
  let categories = $state<Category[]>([]);
  let loadError = $state<Error | null>(null);
  let loaded = $state(false);
  let runs = $state<ImportRun[]>([]);
  let progress = $state<ImportProgress | null>(null);
  let query = $state("");
  let wide = $state(true);

  const slug = $derived(page.params.slug ?? null);
  const category = $derived(page.url.searchParams.get("category") ?? "all");
  const drafts = $derived(page.url.searchParams.get("status") === "draft");
  const adding = $derived(page.url.searchParams.get("add") === "1");

  function toggleAdd(open: boolean) {
    const next = new URL(page.url);
    if (open) {
      next.searchParams.set("add", "1");
    } else {
      next.searchParams.delete("add");
    }
    goto(`${next.pathname}${next.search}`, {
      keepFocus: true,
      noScroll: true,
      replaceState: true,
    });
  }

  function href(
    target: string | null,
    next: { category?: string; drafts?: boolean } = {}
  ) {
    const params = new URLSearchParams();
    const c = next.category ?? category;
    const d = next.drafts ?? drafts;
    if (c !== "all") {
      params.set("category", c);
    }
    if (d) {
      params.set("status", "draft");
    }
    if (adding) {
      params.set("add", "1");
    }
    const q = params.toString();
    const path = target
      ? resolve("/library/[[slug]]", { slug: target })
      : resolve("/library/[[slug]]", {});
    return `${path}${q ? `?${q}` : ""}`;
  }

  async function load() {
    try {
      const [all, cats, history] = await Promise.all([
        listAllInnovations(),
        listCategories(),
        listImportRuns().catch(() => [] as ImportRun[]),
      ]);
      items = all;
      categories = cats;
      runs = history;
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    } finally {
      loaded = true;
    }
  }

  $effect(() => {
    load();
  });

  const offs = [
    live.on("innovation.updated", (data) => {
      const next = data as AdminInnovation;
      const index = items.findIndex((i) => i.slug === next.slug);
      if (index === -1) {
        items = [...items, next];
      } else {
        items[index] = { ...items[index], ...next };
      }
    }),
    live.on("import.progress", (data) => {
      progress = data as ImportProgress;
    }),
    live.on("import.finished", (data) => {
      const run = data as ImportRun;
      progress = null;
      runs = [run, ...runs.filter((r) => r.id !== run.id)];
      load();
    }),
  ];

  onDestroy(() => {
    for (const off of offs) {
      off();
    }
  });

  $effect(() => {
    const media = matchMedia("(min-width: 900px)");
    wide = media.matches;
    const update = () => {
      wide = media.matches;
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  });

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: 0,
      href: href(null, { category: "all" }),
      id: "all",
      note: noteFor(items),
      size: items.length,
      title: "Wszystkie innowacje",
      week: 0,
    },
    ...categories.map((c) => {
      const own = items.filter((i) => i.category.slug === c.slug);
      return {
        cluster: null,
        fresh: 0,
        href: href(null, { category: c.slug }),
        id: c.slug,
        note: noteFor(own),
        size: own.length,
        title: c.name,
        week: 0,
      };
    }),
  ]);

  function noteFor(list: AdminInnovation[]): string {
    const d = list.filter((i) => i.status === "draft").length;
    return d > 0 ? `${d} ${plural(d, "szkic", "szkice", "szkiców")}` : "";
  }

  const normalize = (text: string) =>
    text
      .toLocaleLowerCase("pl")
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "");

  const visible = $derived.by(() => {
    const q = normalize(query.trim());
    return items.filter(
      (i) =>
        (category === "all" || i.category.slug === category) &&
        (!drafts || i.status === "draft") &&
        (q === "" || normalize(`${i.title} ${i.lead ?? ""}`).includes(q))
    );
  });

  const currentCategory = $derived(
    categories.find((c) => c.slug === category) ?? null
  );
  const lastRun = $derived(runs[0] ?? null);
  const running = $derived(progress !== null || lastRun?.status === "running");

  $effect(() => {
    if (wide && !slug && visible.length > 0) {
      goto(href(visible[0].slug), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  async function refreshFromRops(event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    try {
      await runImport();
      progress = {
        created: 0,
        current: null,
        done: 0,
        failed: 0,
        run_id: "",
        skipped_edited: 0,
        total: 0,
        unchanged: 0,
        updated: 0,
      };
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError && e.status === 409
          ? "Import już trwa"
          : "Nie udało się uruchomić importu.",
        "bad"
      );
    }
  }

  function saved(next: AdminInnovation) {
    const index = items.findIndex((i) => i.slug === next.slug);
    if (index !== -1) {
      items[index] = { ...items[index], ...next };
    }
  }

  const runSummary = (run: ImportRun) => {
    if (run.status === "failed") {
      return `Ostatni import ${when(run.started_at)} nie powiódł się${run.error ? `: ${run.error}` : "."}`;
    }
    return `Ostatni import ${when(run.finished_at ?? run.started_at)}: ${run.created} ${plural(run.created, "nowa", "nowe", "nowych")}, ${run.updated} ${plural(run.updated, "zmieniona", "zmienione", "zmienionych")}, ${run.unchanged} bez zmian${run.skipped_edited ? `, ${run.skipped_edited} ${plural(run.skipped_edited, "pominięta", "pominięte", "pominiętych")}, bo ${plural(run.skipped_edited, "zmieniona", "zmienione", "zmienione")} ręcznie` : ""}.`;
  };
</script>

<svelte:head>
  <title>Biblioteka · HubMi</title>
</svelte:head>

<div class={["binder", slug && "has-item"]}>
  <nav aria-label="Kategorie" class="rail">
    <FolderTabs current={category} {tabs} />
  </nav>

  <main class={["board", category === "all" && "first", adding && "adding"]}>
    <header class="bhead">
      <div class="min-w-0">
        <h1
          class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
        >
          {currentCategory?.name ?? "Biblioteka innowacji"}
        </h1>
        <p
          aria-live="polite"
          class="mt-1.5 max-w-[70ch] text-pretty text-hm-ink-soft text-sm"
        >
          {#if progress}
            {progress.total > 0
              ? `Pobieranie z ROPS: ${progress.done} z ${progress.total}${progress.current ? `, teraz ${progress.current}` : ""}.`
              : "Import z ROPS ruszył."}
          {:else if lastRun}
            {runSummary(lastRun)}
          {/if}
        </p>
        {#if progress && progress.total > 0}
          <div aria-hidden="true" class="bar">
            <i style:transform="scaleX({progress.done / progress.total})"></i>
          </div>
        {/if}
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          aria-expanded={adding}
          class="ghost cladd-clickable"
          onclick={() => toggleAdd(!adding)}
          type="button"
        >
          <span class="flex items-center gap-2">
            <svg
              aria-hidden="true"
              fill="none"
              height="16"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.75"
              viewBox="0 0 24 24"
              width="16"
            >
              <path d="M12 5v14M5 12h14" />
            </svg>
            Dodaj materiał
          </span>
        </button>
        <button
          class="ghost cladd-clickable"
          disabled={running}
          onclick={refreshFromRops}
          type="button"
        >
          <span>{running ? "Import trwa…" : "Odśwież z ROPS"}</span>
        </button>
      </div>
    </header>

    {#if adding}
      <MaterialIntake onclose={() => toggleAdd(false)} />
    {/if}

    <div class="work">
      <section aria-label="Lista innowacji" class="register">
        <div class="rhead">
          <label class="search">
            <span class="sr-only">Szukaj w bibliotece</span>
            <svg
              aria-hidden="true"
              fill="none"
              height="16"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-width="1.75"
              viewBox="0 0 24 24"
              width="16"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input
              placeholder="Szukaj po nazwie"
              type="search"
              bind:value={query}
            >
          </label>
          <nav aria-label="Filtr" class="filter">
            <a
              aria-current={drafts ? undefined : "true"}
              data-sveltekit-noscroll
              data-sveltekit-replacestate
              href={href(slug, { drafts: false })}
              >Wszystkie</a
            >
            <a
              aria-current={drafts ? "true" : undefined}
              data-sveltekit-noscroll
              data-sveltekit-replacestate
              href={href(slug, { drafts: true })}
              >Szkice</a
            >
          </nav>
        </div>
        {#if loadError && items.length === 0}
          <ErrorState error={loadError} retry={load} />
        {:else if !loaded}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if visible.length === 0}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">
            {items.length === 0 ? "Biblioteka jest pusta. Użyj przycisku Odśwież z ROPS." : "Nic nie pasuje do wyszukiwania."}
          </p>
        {:else}
          <ol class="rows">
            {#each visible as item (item.slug)}
              <li>
                <a
                  aria-current={item.slug === slug ? "true" : undefined}
                  class={["row", item.status === "draft" && "is-draft"]}
                  data-sveltekit-noscroll
                  data-sveltekit-replacestate
                  href={href(item.slug)}
                >
                  <span class="grid min-w-0 gap-[3px]">
                    <span class="font-semibold text-sm">{item.title}</span>
                    {#if item.lead}
                      <span class="lead">{item.lead}</span>
                    {/if}
                    <span class="text-hm-ink-soft text-xs">
                      {category === "all" ? item.category.name : ""}{category === "all" && item.edited_fields.length > 0 ? " · " : ""}{item.edited_fields.length > 0 ? "zmieniona ręcznie" : ""}
                    </span>
                  </span>
                  <span class="st"
                    >{item.status === "published" ? "Opublikowana" : "Szkic"}</span
                  >
                </a>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      {#if slug}
        <InnovationSheet backHref={href(null)} onsaved={saved} {slug} />
      {/if}
    </div>
  </main>
</div>

<style>
  .binder {
    display: grid;
    grid-template-columns: 264px minmax(0, 1fr);
    min-height: 0;
    padding: 0 18px 18px 10px;
  }

  .rail {
    min-width: 0;
    min-height: 0;
  }

  .board {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    gap: 20px;
    min-width: 0;
    min-height: 0;
    padding: 24px 22px 22px 28px;
    background: var(--hm-board);
    border-radius: 26px;
    box-shadow: inset 1px 1px 0 oklch(1 0 0 / 0.8);
  }

  .board.first {
    border-top-left-radius: 0;
  }

  .board.adding {
    grid-template-rows: auto auto minmax(0, 1fr);
  }

  .bhead {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 24px;
    align-items: end;
  }

  .bar {
    max-width: 420px;
    height: 4px;
    margin-top: 10px;
    overflow: hidden;
    background: var(--hm-sunk);
    border-radius: 4px;
  }

  .bar i {
    display: block;
    height: 100%;
    background: var(--hm-stamp);
    transform-origin: left;
    transition: transform 500ms ease;
  }

  .ghost {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-ink);
    white-space: nowrap;
    background: var(--hm-paper);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-outline);
    transition: background-color 150ms ease;
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  .ghost:disabled {
    color: var(--hm-ink-soft);
  }

  .work {
    display: grid;
    grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
    gap: 18px;
    min-height: 0;
  }

  .register {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr);
    min-height: 0;
    border-top: 1px solid var(--hm-rule);
  }

  .rhead {
    display: flex;
    gap: 10px;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .search {
    display: flex;
    flex: 1;
    gap: 8px;
    align-items: center;
    height: 34px;
    padding: 0 10px;
    color: var(--hm-ink-soft);
    background: var(--hm-sunk);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .search:focus-within {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .search input {
    width: 100%;
    font-size: 13px;
    color: var(--hm-ink);
    outline: none;
    background: none;
    border: 0;
  }

  .search input::placeholder {
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

  .rows {
    position: relative;
    min-height: 0;
    padding: 0 0 8px;
    margin: 0;
    overflow: auto;
    list-style: none;
  }

  .row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: baseline;
    padding: 11px 12px;
    border-bottom: 1px solid var(--hm-rule);
    transition: background-color 150ms ease;
  }

  .row:hover {
    background: color-mix(in oklab, var(--hm-stamp) 5%, transparent);
  }

  .row:focus-visible {
    outline-offset: -2px;
    border-radius: 12px;
  }

  .row[aria-current="true"] {
    background: var(--hm-stamp-wash);
    border-bottom-color: transparent;
    border-radius: 12px;
  }

  .lead {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 13px;
    line-height: 1.4;
    color: var(--hm-ink-soft);
  }

  .st {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ok);
    white-space: nowrap;
  }

  .st::before {
    width: 6px;
    height: 6px;
    content: "";
    background: currentColor;
    border-radius: 50%;
  }

  .is-draft .st {
    color: var(--hm-ink-soft);
  }

  @media (max-width: 899px) {
    .binder {
      grid-template-rows: auto 1fr;
      grid-template-columns: minmax(0, 1fr);
      padding: 0 10px 10px;
    }

    .rail {
      overflow-x: auto;
      scrollbar-width: none;
    }

    .board,
    .board.first {
      padding: 16px 12px 12px;
      border-radius: 0 0 22px 22px;
    }

    .bhead,
    .work {
      grid-template-columns: minmax(0, 1fr);
    }

    .bhead .ghost {
      justify-self: start;
      height: 44px;
    }

    .has-item .register,
    .has-item .bhead,
    .has-item .rail {
      display: none;
    }

    .has-item .board {
      padding: 0;
      background: none;
      box-shadow: none;
    }
  }
</style>
