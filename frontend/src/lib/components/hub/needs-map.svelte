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
  let hovered = $state<string | null>(null);
  let focused = $state<string | null>(null);

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
    return features.map((f) => {
      const outer = rings(f)
        .map((ring) => ring.map((p) => project(p)))
        .sort((a, b) => b.length - a.length)[0] ?? [[0, 0]];
      const xs = outer.map(([x]) => x);
      const ys = outer.map(([, y]) => y);
      return {
        cx: (Math.min(...xs) + Math.max(...xs)) / 2,
        cy: (Math.min(...ys) + Math.max(...ys)) / 2,
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
      };
    });
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

  const preview = $derived(focused ?? hovered);
  const shapeOf = (slug: string | null) =>
    slug ? (shapes.find((x) => x.slug === slug) ?? null) : null;
  const selectedShape = $derived(shapeOf(selected));
  const previewShape = $derived(preview === selected ? null : shapeOf(preview));
  const labelShape = $derived(previewShape ?? selectedShape);
  const current = $derived(
    preview || selected ? (bySlug.get(preview ?? selected ?? "") ?? null) : null
  );
  const busiest = $derived(
    [...(data?.powiats ?? [])].sort((a, b) => b.needs_count - a.needs_count)[0]
  );
  const shownSlug = $derived(preview ?? selected);
  const shown = $derived(
    current ??
      (shownSlug
        ? {
            name: shapeOf(shownSlug)?.name ?? "",
            needs_count: 0,
            needs_recent: 0,
            slug: shownSlug,
            top_clusters: [],
          }
        : (busiest ?? null))
  );

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
          onblur={() => {
            if (focused === s.slug) {
              focused = null;
            }
          }}
          onclick={() => {
            selected = selected === s.slug ? null : s.slug;
          }}
          onfocus={(event) => {
            if (event.currentTarget.matches(":focus-visible")) {
              focused = s.slug;
            }
          }}
          onkeydown={(event) => keydown(event, s.slug)}
          onpointerenter={() => {
            hovered = s.slug;
          }}
          onpointerleave={() => {
            if (hovered === s.slug) {
              hovered = null;
            }
          }}
          role="button"
          tabindex="0"
        >
          <title>{s.name}</title>
        </path>
      {/each}
      <g aria-hidden="true" class="marks">
        {#if selectedShape}
          <path class="halo sel" d={selectedShape.d} />
          <path class="line sel" d={selectedShape.d} />
        {/if}
        {#if previewShape}
          <path class="halo" d={previewShape.d} />
          <path class={["line", focused && "ring"]} d={previewShape.d} />
        {/if}
        {#if labelShape}
          <text class="name" x={labelShape.cx} y={labelShape.cy}>
            {labelShape.name}
          </text>
        {/if}
      </g>
    </svg>
    <div class="side">
      {#if shown}
        <h3 class="font-semibold text-base">{shown.name}</h3>
        <p class="text-sm">
          <b class="tabular text-[26px] tracking-tight">{shown.needs_count}</b>
          {plural(shown.needs_count, "potrzeba", "potrzeby", "potrzeb")}
          od początku,
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
        Razem od początku
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

  .marks path {
    pointer-events: none;
    fill: none;
    stroke-linejoin: round;
  }

  .marks .halo {
    stroke: var(--hm-paper);
    stroke-width: 5;
  }

  .marks .line {
    stroke: var(--hm-ink);
    stroke-width: 1.75;
  }

  .marks .halo.sel {
    stroke-width: 6.5;
  }

  .marks .line.sel {
    stroke-width: 3;
  }

  .marks .line.ring {
    stroke: var(--hm-ring);
    stroke-width: 2.5;
  }

  .name {
    font-size: 13px;
    font-weight: 650;
    dominant-baseline: middle;
    pointer-events: none;
    text-anchor: middle;
    fill: var(--hm-ink);
    stroke: var(--hm-paper);
    stroke-width: 4px;
    stroke-linejoin: round;
    paint-order: stroke;
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
