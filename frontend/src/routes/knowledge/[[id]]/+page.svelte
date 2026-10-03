<script lang="ts">
  import { onDestroy } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminChallenge,
    type AdminMaterial,
    challengeAreas,
    type KnowledgeRun,
    knowledgeRuns,
    listChallenges,
    listMaterials,
    type Ref,
    runKnowledgeImport,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import KnowledgeSheet from "$lib/components/hub/knowledge-sheet.svelte";
  import type { FolderTab } from "$lib/components/hub/types";
  import { plural, when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  type Item =
    | { kind: "challenge"; value: AdminChallenge }
    | { kind: "material"; value: AdminMaterial };

  const MATERIALS = "materialy";

  let challenges = $state<AdminChallenge[]>([]);
  let materials = $state<AdminMaterial[]>([]);
  let areas = $state<Ref[]>([]);
  let runs = $state<KnowledgeRun[]>([]);
  let progress = $state<{
    done: number;
    step: string | null;
    total: number;
  } | null>(null);
  let loadError = $state<Error | null>(null);
  let loaded = $state(false);
  let query = $state("");
  let wide = $state(true);

  const id = $derived(page.params.id ?? null);
  const section = $derived(page.url.searchParams.get("obszar") ?? "all");
  const unchecked = $derived(
    page.url.searchParams.get("stan") === "niesprawdzone"
  );

  function href(
    target: string | null,
    next: { section?: string; unchecked?: boolean } = {}
  ) {
    const params = new URLSearchParams();
    const s = next.section ?? section;
    const u = next.unchecked ?? unchecked;
    if (s !== "all") {
      params.set("obszar", s);
    }
    if (u) {
      params.set("stan", "niesprawdzone");
    }
    const q = params.toString();
    const path = target
      ? resolve("/knowledge/[[id]]", { id: target })
      : resolve("/knowledge/[[id]]", {});
    return `${path}${q ? `?${q}` : ""}`;
  }

  async function load() {
    try {
      const [c, m, a, r] = await Promise.all([
        listChallenges(),
        listMaterials(),
        challengeAreas(),
        knowledgeRuns().catch(() => [] as KnowledgeRun[]),
      ]);
      challenges = c;
      materials = m;
      areas = a;
      runs = r;
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
    live.on("knowledge.import.progress", (data) => {
      const d = data as { done?: number; step?: string | null; total?: number };
      progress = {
        done: d.done ?? 0,
        step: d.step ?? null,
        total: d.total ?? 0,
      };
    }),
    live.on("knowledge.import.finished", () => {
      progress = null;
      load();
    }),
    live.on("material.updated", (data) => {
      const next = data as AdminMaterial;
      materials = materials.map((m) =>
        m.id === next.id ? { ...m, ...next } : m
      );
    }),
    live.on("challenge.updated", (data) => {
      const next = data as AdminChallenge;
      challenges = challenges.map((c) =>
        c.id === next.id ? { ...c, ...next } : c
      );
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

  const uncheckedNote = (list: AdminChallenge[]) => {
    const n = list.filter((c) => !c.verified).length;
    return n > 0 ? `${n} do sprawdzenia` : "";
  };

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: 0,
      href: href(null, { section: "all" }),
      id: "all",
      note: uncheckedNote(challenges),
      size: challenges.length,
      title: "Wyzwania regionu",
      week: 0,
    },
    ...areas.map((a) => {
      const own = challenges.filter((c) => c.area.slug === a.slug);
      return {
        cluster: null,
        fresh: 0,
        href: href(null, { section: a.slug }),
        id: a.slug,
        note: uncheckedNote(own),
        size: own.length,
        title: a.name,
        week: 0,
      };
    }),
    {
      cluster: null,
      fresh: 0,
      href: href(null, { section: MATERIALS }),
      id: MATERIALS,
      note: "",
      size: materials.length,
      title: "Materiały ROPS",
      week: 0,
    },
  ]);

  const normalize = (text: string) =>
    text
      .toLocaleLowerCase("pl")
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "");

  const visible = $derived.by((): Item[] => {
    const q = normalize(query.trim());
    const hit = (t: string) => q === "" || normalize(t).includes(q);
    if (section === MATERIALS) {
      return materials
        .filter((m) => hit(`${m.title} ${m.summary ?? ""}`))
        .map((value) => ({ kind: "material", value }));
    }
    return challenges
      .filter(
        (c) =>
          (section === "all" || c.area.slug === section) &&
          !(unchecked && c.verified) &&
          hit(`${c.title} ${c.summary}`)
      )
      .map((value) => ({ kind: "challenge", value }));
  });

  const current = $derived(visible.find((i) => i.value.id === id) ?? null);
  const lastRun = $derived(runs[0] ?? null);
  const running = $derived(progress !== null || lastRun?.status === "running");
  const heading = $derived(
    section === MATERIALS
      ? "Materiały ROPS"
      : (areas.find((a) => a.slug === section)?.name ?? "Wyzwania regionu")
  );

  $effect(() => {
    if (wide && !current && visible.length > 0) {
      goto(href(visible[0].value.id), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  async function startImport(event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    try {
      await runKnowledgeImport();
      progress = { done: 0, step: null, total: 0 };
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

  function saved(next: Item) {
    if (next.kind === "challenge") {
      challenges = challenges.map((c) =>
        c.id === next.value.id ? next.value : c
      );
    } else {
      materials = materials.map((m) =>
        m.id === next.value.id ? next.value : m
      );
    }
  }

  const steps: Record<string, string> = {
    challenges: "wyzwania",
    figures: "liczby dla powiatów",
    materials: "dokumenty",
  };
  const status = $derived.by(() => {
    const p = progress ?? (lastRun?.status === "running" ? lastRun : null);
    if (p) {
      return p.total > 0
        ? `Pobieranie z ROPS${p.step ? ` (${steps[p.step] ?? p.step})` : ""}: ${p.done} z ${p.total}.`
        : "Import z ROPS ruszył.";
    }
    if (lastRun) {
      return lastRun.status === "failed"
        ? `Ostatni import ${when(lastRun.started_at)} nie powiódł się.`
        : `Ostatni import ${when(lastRun.finished_at ?? lastRun.started_at)}.`;
    }
    return "";
  });
</script>

<svelte:head>
  <title>Wiedza · HubMi</title>
</svelte:head>

<div class={["binder", id && "has-item"]}>
  <nav aria-label="Obszary" class="rail">
    <FolderTabs current={section} {tabs} />
  </nav>

  <main class={["board", section === "all" && "first"]}>
    <header class="bhead">
      <div class="min-w-0">
        <h1
          class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
        >
          {heading}
        </h1>
        <p aria-live="polite" class="mt-1.5 text-hm-ink-soft text-sm">
          {status}
        </p>
      </div>
      <button
        class="ghost cladd-clickable"
        disabled={running}
        onclick={startImport}
        type="button"
      >
        <span>{running ? "Import trwa…" : "Odśwież z ROPS"}</span>
      </button>
    </header>

    <div class="work">
      <section aria-label="Lista" class="register">
        <div class="rhead">
          <label class="search">
            <span class="sr-only">Szukaj</span>
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
              placeholder="Szukaj po tytule"
              type="search"
              bind:value={query}
            >
          </label>
          {#if section !== MATERIALS}
            <nav aria-label="Filtr" class="filter">
              <a
                aria-current={unchecked ? undefined : "true"}
                data-sveltekit-noscroll
                data-sveltekit-replacestate
                href={href(id, { unchecked: false })}
                >Wszystkie</a
              >
              <a
                aria-current={unchecked ? "true" : undefined}
                data-sveltekit-noscroll
                data-sveltekit-replacestate
                href={href(id, { unchecked: true })}
                >Do sprawdzenia</a
              >
            </nav>
          {/if}
        </div>
        {#if loadError && !loaded}
          <ErrorState error={loadError} retry={load} />
        {:else if !loaded}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if visible.length === 0}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">
            {challenges.length + materials.length === 0 ? "Zasobnik jest pusty. Użyj przycisku Odśwież z ROPS." : "Nic tutaj nie ma."}
          </p>
        {:else}
          <ol class="rows">
            {#each visible as item (item.value.id)}
              <li>
                <a
                  aria-current={item.value.id === id ? "true" : undefined}
                  class="row"
                  data-sveltekit-noscroll
                  data-sveltekit-replacestate
                  href={href(item.value.id)}
                >
                  <span class="grid min-w-0 gap-[3px]">
                    <span class="font-semibold text-sm"
                      >{item.value.title}</span
                    >
                    {#if item.value.summary}
                      <span class="lead">{item.value.summary}</span>
                    {/if}
                    {#if item.kind === "material"}
                      <span class="text-hm-ink-soft text-xs"
                        >{item.value.kind.name}{item.value.year ? `, ${item.value.year}` : ""}</span
                      >
                    {:else if section === "all"}
                      <span class="text-hm-ink-soft text-xs"
                        >{item.value.area.name}
                        · {item.value.figures.length}
                        {plural(item.value.figures.length, "liczba", "liczby", "liczb")}</span
                      >
                    {/if}
                  </span>
                  {#if item.kind === "challenge"}
                    <span class={["st", item.value.verified && "ok"]}
                      >{item.value.verified ? "Sprawdzone" : "Do sprawdzenia"}</span
                    >
                  {:else}
                    <span
                      class={["st", item.value.status === "published" && "ok"]}
                      >{item.value.status === "published" ? "Opublikowany" : "Szkic"}</span
                    >
                  {/if}
                </a>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      {#if current}
        <KnowledgeSheet backHref={href(null)} item={current} onsaved={saved} />
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

  .bhead {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 24px;
    align-items: end;
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
    white-space: nowrap;
    border-radius: 8px;
  }

  .filter a[aria-current="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  .rows {
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

    .rhead {
      flex-wrap: wrap;
    }

    .row {
      grid-template-columns: minmax(0, 1fr);
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
