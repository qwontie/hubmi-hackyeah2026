<script lang="ts">
  import { resolve } from "$app/paths";
  import { api } from "$lib/api/client";
  import { plural } from "$lib/format";

  interface Feature {
    geometry: {
      coordinates: number[][][] | number[][][][];
      type: "Polygon" | "MultiPolygon";
    };
    id: string;
    properties: { name: string; slug: string };
  }

  interface PowiatNeeds {
    name: string;
    needs_count: number;
    needs_recent: number;
    slug: string;
    top_clusters: { count: number; id: string; title: string }[];
  }

  interface AdminMap {
    needs_total: number;
    needs_without_powiat: number;
    powiats: PowiatNeeds[];
    recent_days: number;
  }

  let { days }: { days: number } = $props();

  const W = 560;
  const H = 440;
  const PAD = 8;

  let features = $state<Feature[]>([]);
  let data = $state<AdminMap | null>(null);
  let failed = $state(false);
  let selected = $state<string | null>(null);

  $effect(() => {
    api
      .get<{ features: Feature[] }>("/map/powiats.geojson")
      .then(({ features: next }) => {
        features = next;
      })
      .catch(() => {
        failed = true;
      });
  });

  $effect(() => {
    api
      .get<AdminMap>("/admin/map", { days })
      .then((m) => {
        data = m;
      })
      .catch(() => {
        failed = true;
      });
  });

  const rings = (f: Feature): number[][][] =>
    f.geometry.type === "Polygon"
      ? (f.geometry.coordinates as number[][][])
      : (f.geometry.coordinates as number[][][][]).flat();

  const projection = $derived.by(() => {
    const points = features.flatMap((f) => rings(f).flat());
    if (points.length === 0) {
      return null;
    }
    const lons = points.map((p) => p[0]);
    const lats = points.map((p) => p[1]);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
    const scale = Math.min(
      (W - PAD * 2) / ((maxLon - minLon) * k),
      (H - PAD * 2) / (maxLat - minLat)
    );
    const offX = (W - (maxLon - minLon) * k * scale) / 2;
    const offY = (H - (maxLat - minLat) * scale) / 2;
    return (p: number[]) => [
      offX + (p[0] - minLon) * k * scale,
      offY + (maxLat - p[1]) * scale,
    ];
  });

  const shapes = $derived.by(() => {
    const project = projection;
    if (!project) {
      return [];
    }
    return features.map((f) => ({
      d: rings(f)
        .map(
          (ring) =>
            `M${ring
              .map((p) => project(p))
              .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
              .join("L")}Z`
        )
        .join(""),
      name: f.properties.name,
      slug: f.properties.slug,
    }));
  });

  const bySlug = $derived(
    new Map((data?.powiats ?? []).map((p) => [p.slug, p]))
  );
  const max = $derived(
    Math.max(1, ...(data?.powiats ?? []).map((p) => p.needs_count))
  );

  const steps = [
    "var(--hm-board)",
    "oklch(0.9 0.04 280)",
    "oklch(0.8 0.08 280)",
    "oklch(0.64 0.13 280)",
    "var(--hm-stamp)",
  ];
  const fill = (slug: string) => {
    const n = bySlug.get(slug)?.needs_count ?? 0;
    if (n === 0) {
      return steps[0];
    }
    return steps[max <= 1 ? 4 : 1 + Math.round(((n - 1) / (max - 1)) * 3)];
  };

  const current = $derived(selected ? (bySlug.get(selected) ?? null) : null);
  const busiest = $derived(
    [...(data?.powiats ?? [])].sort((a, b) => b.needs_count - a.needs_count)[0]
  );
  const shown = $derived(current ?? busiest ?? null);

  function keydown(event: KeyboardEvent, slug: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selected = slug;
    }
  }
</script>

{#if failed && !data}
  <p class="text-hm-ink-soft text-sm">Mapa jest teraz niedostępna.</p>
{:else if shapes.length === 0 || !data}
  <p class="text-hm-ink-soft text-sm">Wczytywanie mapy…</p>
{:else}
  <div class="wrap">
    <!-- biome-ignore lint/a11y/useSemanticElements: an svg map groups its powiat shapes -->
    <svg
      aria-label="Mapa Małopolski: liczba potrzeb w powiatach"
      role="group"
      viewBox="0 0 {W} {H}"
    >
      {#each shapes as s (s.slug)}
        <!-- biome-ignore lint/a11y/useSemanticElements: svg paths cannot be buttons -->
        <path
          aria-label="{s.name}: {bySlug.get(s.slug)?.needs_count ?? 0} {plural(bySlug.get(s.slug)?.needs_count ?? 0, 'potrzeba', 'potrzeby', 'potrzeb')}"
          aria-pressed={selected === s.slug}
          class={[selected === s.slug && "on"]}
          d={s.d}
          fill={fill(s.slug)}
          onclick={() => {
            selected = s.slug;
          }}
          onkeydown={(event) => keydown(event, s.slug)}
          role="button"
          tabindex="0"
        >
          <title>{s.name}</title>
        </path>
      {/each}
    </svg>
    <div class="side">
      {#if shown}
        <h3 class="font-semibold text-base">{shown.name}</h3>
        <p class="text-sm">
          <b class="tabular text-[26px] tracking-tight">{shown.needs_count}</b>
          {plural(shown.needs_count, "potrzeba", "potrzeby", "potrzeb")},
          {shown.needs_recent}
          w&nbsp;ostatnich {data.recent_days} dniach
        </p>
        {#if shown.top_clusters.length > 0}
          <ul class="mt-2 grid gap-1.5">
            {#each shown.top_clusters as c (c.id)}
              <li class="text-sm">
                <a class="link" href="{resolve('/needs')}?folder={c.id}"
                  >{c.title}</a
                > <span class="text-hm-ink-soft tabular">{c.count}</span>
              </li>
            {/each}
          </ul>
        {/if}
      {/if}
      <div aria-hidden="true" class="legend">
        {#each steps as color, i (i)}
          <i style:background={color}></i>
        {/each}
        <span>0</span><span>{max}</span>
      </div>
      <p class="text-hm-ink-soft text-xs">
        Razem
        {data.needs_total}{data.needs_without_powiat > 0 ? `, w tym ${data.needs_without_powiat} bez powiatu` : ""}.
        Granice: GUGiK (PRG).
      </p>
    </div>
  </div>
{/if}

<style>
  .wrap {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
    gap: 20px;
    align-items: start;
  }

  svg {
    width: 100%;
    height: auto;
  }

  path {
    cursor: pointer;
    outline: none;
    stroke: var(--hm-paper);
    stroke-width: 1.2;
    transition: fill 150ms ease;
  }

  path:hover {
    filter: brightness(0.94);
  }

  path:focus-visible,
  path.on {
    stroke: var(--hm-ink);
    stroke-width: 2;
  }

  .side {
    display: grid;
    gap: 6px;
  }

  .link {
    font-weight: 600;
  }

  .link:hover {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .legend {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 2px;
    max-width: 200px;
    margin-top: 10px;
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  .legend i {
    height: 8px;
    border-radius: 2px;
    box-shadow: inset 0 0 0 1px var(--hm-rule);
  }

  .legend span:last-child {
    grid-column: 5;
    text-align: right;
  }

  @media (max-width: 899px) {
    .wrap {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
