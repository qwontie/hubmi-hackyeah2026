<script lang="ts">
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminNeed,
    type DemandRow,
    listAllNeeds,
    listCategories,
    listDemand,
  } from "$lib/api/admin";
  import { api } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import DayChart from "$lib/components/hub/day-chart.svelte";
  import NeedsMap from "$lib/components/hub/needs-map.svelte";
  import { nbsp, periodWords, plural } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import Challenges from "./challenges.svelte";

  interface Ranked {
    count: number;
    name: string;
    slug: string | null;
  }

  interface Stats {
    ai: { calls: number; cost_usd: number; failed: number };
    by_category: Ranked[];
    by_powiat: Ranked[];
    feedback: {
      does_not_fit: number;
      fit_share: number | null;
      fits: number;
      improvements: number;
      most_rejected: {
        does_not_fit: number;
        fits: number;
        slug: string;
        title: string;
      }[];
      test_signups: number;
    };
    growing_clusters: {
      current: number;
      growth: number;
      id: string;
      previous: number;
      size: number;
      title: string;
    }[];
    per_day: { needs: number; nothing_fits: number; start: string }[];
    searches: {
      by_category: Ranked[];
      degraded: number;
      no_match: number;
      no_result_share: number;
      ok: number;
      total: number;
      unclear: number;
    };
    top_clusters: {
      current: number;
      growth: number;
      id: string;
      previous: number;
      size: number;
      title: string;
    }[];
    top_innovations: {
      avg_score: number;
      matches: number;
      slug: string;
      title: string;
      top_matches: number;
    }[];
    totals: {
      answered: number;
      closed: number;
      junk: number;
      median_first_reply_hours: number | null;
      needs: number;
      needs_previous: number;
      nothing_fits: number;
      nothing_fits_share: number;
      replies: number;
      waiting: number;
      with_contact: number;
    };
  }

  const periods = [
    { id: "7d", label: "7 dni" },
    { id: "30d", label: "30 dni" },
    { id: "90d", label: "90 dni" },
    { id: "365d", label: "Rok" },
  ];

  let stats = $state<Stats | null>(null);
  let loadError = $state<Error | null>(null);
  let allNeeds = $state<AdminNeed[] | null>(null);
  let categoryNames = $state<Map<string, string>>(new Map());
  let demand = $state<DemandRow[] | null>(null);

  async function loadBreakdown() {
    try {
      const [needs, cats] = await Promise.all([
        listAllNeeds(),
        listCategories(),
      ]);
      allNeeds = needs;
      categoryNames = new Map(cats.map((c) => [c.slug, c.name]));
    } catch {
      allNeeds = null;
    }
    try {
      demand = (await listDemand()).items;
    } catch {
      demand = null;
    }
  }

  const period = $derived(page.url.searchParams.get("period") ?? "30d");

  function periodHref(id: string) {
    const params = new URLSearchParams(page.url.searchParams);
    params.set("period", id);
    return `${resolve("/stats")}?${params}`;
  }

  async function load(p: string) {
    try {
      stats = await api.get<Stats>("/admin/stats", { period: p });
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    load(period);
    loadBreakdown();
  });

  $effect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    const again = () => {
      if (timer) {
        clearTimeout(timer);
      }
      timer = setTimeout(() => {
        load(period);
        loadBreakdown();
      }, 1500);
    };
    const offs = [
      live.on("need.created", again),
      live.on("need.updated", again),
    ];
    return () => {
      for (const off of offs) {
        off();
      }
    };
  });

  const pct = (v: number | null | undefined) =>
    v === null || v === undefined ? "brak danych" : `${Math.round(v * 100)}%`;
  const hours = (h: number | null) => {
    if (h === null) {
      return "brak danych";
    }
    if (h < 1) {
      return `${Math.max(1, Math.round(h * 60))} min`;
    }
    return `${h.toLocaleString("pl-PL", { maximumFractionDigits: 1 })} godz.`;
  };

  const delta = $derived.by(() => {
    if (!stats) {
      return "";
    }
    const d = stats.totals.needs - stats.totals.needs_previous;
    if (stats.totals.needs_previous === 0) {
      return "brak danych z poprzedniego okresu";
    }
    return `${d >= 0 ? "+" : ""}${d} wobec poprzedniego okresu`;
  });

  const days = $derived(stats?.per_day ?? []);
  const window = $derived(periodWords[period] ?? periodWords["30d"]);
  const noResult = $derived(
    stats ? stats.searches.unclear + stats.searches.no_match : 0
  );

  const demandNote = (d: DemandRow) =>
    d.with_email > 0 ? `, ${d.with_email} z e-mailem` : "";
  const topOf = (list: Ranked[]) => list.slice(0, 8);
  const maxOf = (list: Ranked[]) => Math.max(1, ...list.map((r) => r.count));
</script>

<svelte:head>
  <title>Statystyki · HubMi</title>
</svelte:head>

<main class="board">
  <header class="flex flex-wrap items-end justify-between gap-4">
    <h1
      class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
    >
      Statystyki
    </h1>
    <nav aria-label="Okres" class="filter">
      {#each periods as p (p.id)}
        <a
          aria-current={p.id === period ? "true" : undefined}
          data-sveltekit-noscroll
          data-sveltekit-replacestate
          href={periodHref(p.id)}
          >{p.label}</a
        >
      {/each}
    </nav>
  </header>

  {#if loadError && !stats}
    <ErrorState error={loadError} retry={() => load(period)} />
  {:else if !stats}
    <p class="text-hm-ink-soft text-sm">Wczytywanie…</p>
  {:else}
    <dl class="figures">
      <div>
        <dt>Potrzeby {window}</dt>
        <dd class="tabular">{stats.totals.needs}</dd>
        <dd class="note">{delta}</dd>
      </div>
      <div>
        <dt>Czekają na odpowiedź teraz</dt>
        <dd class="tabular">{stats.totals.waiting}</dd>
        <dd class="note">
          {window}: {stats.totals.answered}
          z&nbsp;odpowiedzią, {stats.totals.closed}
          {plural(stats.totals.closed, "zamknięta", "zamknięte", "zamkniętych")}
        </dd>
      </div>
      <div>
        <dt>Pierwsza odpowiedź</dt>
        <dd class="tabular">{hours(stats.totals.median_first_reply_hours)}</dd>
        <dd class="note">mediana od zgłoszenia, {window}</dd>
      </div>
      <div>
        <dt>Wyszukiwania bez wyniku</dt>
        <dd class="tabular">
          {stats.searches.total > 0 ? pct(stats.searches.no_result_share) : "brak"}
        </dd>
        <dd class="note">
          {window}: {noResult}
          z&nbsp;{stats.searches.total}
          {plural(stats.searches.total, "wyszukiwania", "wyszukiwań", "wyszukiwań")}
          mieszkańców, bez zapisu treści
        </dd>
      </div>
      <div>
        <dt>Ocena mieszkańców: pasuje</dt>
        <dd class="tabular">
          {stats.feedback.fits + stats.feedback.does_not_fit > 0 ? pct(stats.feedback.fit_share) : "brak ocen"}
        </dd>
        <dd class="note">
          {window}: pasuje {stats.feedback.fits}, nie pasuje
          {stats.feedback.does_not_fit}
        </dd>
      </div>
      <div>
        <dt>Zgłoszenia wolontariuszy</dt>
        <dd class="tabular">{stats.feedback.test_signups}</dd>
        <dd class="note">
          {window}, {stats.feedback.improvements}
          {plural(stats.feedback.improvements, "pomysł na ulepszenie", "pomysły na ulepszenie", "pomysłów na ulepszenie")}
        </dd>
      </div>
    </dl>

    <section aria-labelledby="chart-h" class="panel">
      <h2 class="h" id="chart-h">
        Nowe potrzeby dzień po dniu <span class="win">{window}</span>
      </h2>
      <DayChart {days} names={categoryNames} needs={allNeeds} />
    </section>

    <section aria-labelledby="map-h" class="panel">
      <h2 class="h" id="map-h">
        Potrzeby w&nbsp;powiatach
        <span class="win">od początku</span>
      </h2>
      <NeedsMap days={Number.parseInt(period, 10) || 30} />
    </section>

    <div class="grid3">
      <section aria-labelledby="grow-h" class="panel">
        <h2 class="h" id="grow-h">
          Rosnące teczki <span class="win">{window}</span>
        </h2>
        {#if stats.growing_clusters.length === 0}
          <p class="empty">
            Żadna teczka nie rośnie szybciej niż w&nbsp;poprzednim okresie.
          </p>
        {:else}
          <ol class="list">
            {#each stats.growing_clusters.slice(0, 8) as c (c.id)}
              <li>
                <a href="{resolve('/needs')}?folder={c.id}">{nbsp(c.title)}</a>
                <span class="tabular"
                  ><b>+{c.growth}</b>
                  ({c.previous}
                  → {c.current})</span
                >
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      <section aria-labelledby="pow-h" class="panel">
        <h2 class="h" id="pow-h">Powiaty <span class="win">{window}</span></h2>
        {#if stats.by_powiat.length === 0}
          <p class="empty">Brak potrzeb w&nbsp;tym okresie.</p>
        {:else}
          <ol class="bars">
            {#each topOf(stats.by_powiat) as r (r.slug ?? r.name)}
              <li>
                <span>{r.name}</span><span class="tabular">{r.count}</span
                ><i
                  style:width="{(r.count / maxOf(stats.by_powiat)) * 100}%"
                ></i>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      <section aria-labelledby="cat-h" class="panel">
        <h2 class="h" id="cat-h">Obszary <span class="win">{window}</span></h2>
        {#if stats.by_category.length === 0}
          <p class="empty">Brak potrzeb w&nbsp;tym okresie.</p>
        {:else}
          <ol class="bars">
            {#each topOf(stats.by_category) as r (r.slug ?? r.name)}
              <li>
                <span>{r.name}</span><span class="tabular">{r.count}</span
                ><i
                  style:width="{(r.count / maxOf(stats.by_category)) * 100}%"
                ></i>
              </li>
            {/each}
          </ol>
        {/if}
      </section>
    </div>

    <Challenges />

    <div class="grid2">
      <section aria-labelledby="inn-h" class="panel">
        <h2 class="h" id="inn-h">
          Najczęściej proponowane w&nbsp;wyszukiwaniach
          <span class="win">{window}</span>
        </h2>
        {#if stats.top_innovations.length === 0}
          <p class="empty">
            Jeszcze nic nie zaproponowano: liczymy od wyszukiwań mieszkańców na
            stronie, bez zapisu treści.
          </p>
        {:else}
          <ol class="list">
            {#each stats.top_innovations.slice(0, 8) as i (i.slug)}
              <li>
                <a href="{resolve('/library')}/{i.slug}">{i.title}</a>
                <span class="tabular"
                  >{i.matches} {plural(i.matches, "raz", "razy", "razy")},
                  {i.top_matches}
                  na pierwszym miejscu</span
                >
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      <section aria-labelledby="dem-h" class="panel">
        <h2 class="h" id="dem-h">
          "Chcę tego u&nbsp;siebie" <span class="win">od początku</span>
        </h2>
        {#if demand === null}
          <p class="empty">Wczytywanie…</p>
        {:else if demand.length === 0}
          <p class="empty">
            Nikt jeszcze nie zaznaczył, że chce innowacji u&nbsp;siebie.
          </p>
        {:else}
          <ol class="list">
            {#each demand.slice(0, 8) as d (`${d.innovation.slug}:${d.powiat}`)}
              <li>
                <a href="{resolve('/library')}/{d.innovation.slug}"
                  >{d.innovation.title}</a
                >
                <span class="tabular"
                  >{d.powiat_name}: <b>{d.count}</b>{demandNote(d)}</span
                >
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      <section aria-labelledby="rej-h" class="panel">
        <h2 class="h" id="rej-h">
          Najczęściej oceniane jako niepasujące
          <span class="win">{window}</span>
        </h2>
        {#if stats.feedback.most_rejected.length === 0}
          <p class="empty">
            Nikt jeszcze nie ocenił propozycji jako niepasującej.
          </p>
        {:else}
          <ol class="list">
            {#each stats.feedback.most_rejected.slice(0, 8) as i (i.slug)}
              <li>
                <a href="{resolve('/library')}/{i.slug}">{i.title}</a>
                <span class="tabular"
                  >Nie pasuje: {i.does_not_fit}, pasuje: {i.fits}</span
                >
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
    position: relative;
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
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    border-radius: 8px;
  }

  .filter a[aria-current="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  .figures {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    margin: 0;
    border-top: 1px solid var(--hm-rule);
    border-bottom: 1px solid var(--hm-rule);
  }

  .figures div {
    display: grid;
    gap: 4px;
    align-content: start;
    padding: 14px 16px 14px 0;
  }

  .figures div + div {
    padding-left: 16px;
    border-left: 1px solid var(--hm-rule);
  }

  .figures dt {
    order: 1;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .figures dd:not(.note) {
    order: 2;
    margin: 0;
    font-size: 26px;
    font-weight: 650;
    line-height: 1.1;
    letter-spacing: -0.03em;
  }

  .figures .note {
    order: 3;
    margin: 0;
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  .panel {
    min-width: 0;
    padding: 18px 20px;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: 0 0 0 1px var(--hm-rule);
  }

  .h {
    margin-bottom: 12px;
    font-size: 14px;
    font-weight: 650;
  }

  .win {
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .grid3 {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  .grid2 {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .list,
  .bars {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .list li {
    display: grid;
    gap: 2px;
    padding: 8px 0;
    font-size: 13px;
    border-bottom: 1px solid var(--hm-rule);
  }

  .list li:last-child {
    border-bottom: 0;
  }

  .list a {
    font-size: 14px;
    font-weight: 600;
  }

  .list a:hover {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .list span {
    color: var(--hm-ink-soft);
  }

  .list b {
    color: var(--hm-stamp);
  }

  .bars li {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 4px 10px;
    padding: 6px 0;
    font-size: 13px;
  }

  .bars i {
    display: block;
    grid-column: 1 / -1;
    height: 6px;
    background: var(--hm-stamp);
    border-radius: 6px;
  }

  .empty {
    font-size: 13px;
    color: var(--hm-ink-soft);
  }

  @media (max-width: 1180px) {
    .figures {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .figures div:nth-child(4) {
      padding-left: 0;
      border-left: 0;
    }

    .figures div:nth-child(n + 4) {
      border-top: 1px solid var(--hm-rule);
    }
  }

  @media (max-width: 899px) {
    .board {
      padding: 16px 12px;
      margin: 0 10px 10px;
      border-radius: 22px;
    }

    .figures {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .figures div,
    .figures div + div {
      padding: 12px 8px 12px 0;
      border-left: 0;
    }

    .figures div:nth-child(n + 3) {
      border-top: 1px solid var(--hm-rule);
    }

    .grid3,
    .grid2 {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
