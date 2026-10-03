<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type Adaptation,
    type AdminAdaptation,
    getAdaptation,
    listAdaptations,
  } from "$lib/api/admin";
  import ErrorState from "$lib/components/error-state.svelte";
  import { dayWords, nbsp, plural, powiatName, when } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { live } from "$lib/live/stream.svelte";

  const WEEK = 7 * 86_400_000;

  let plans = $state<AdminAdaptation[]>([]);
  let total = $state(0);
  let loaded = $state(false);
  let loadError = $state<Error | null>(null);
  let detail = $state<Adaptation | null>(null);
  let detailError = $state<Error | null>(null);
  let wide = $state(true);
  let controller: AbortController | null = null;

  const id = $derived(page.params.id ?? null);

  const hrefFor = (target: string | null) =>
    target
      ? resolve("/adaptations/[[id]]", { id: target })
      : resolve("/adaptations/[[id]]", {});

  async function load() {
    try {
      const { items, total: count } = await listAdaptations({});
      plans = items;
      total = count;
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    } finally {
      loaded = true;
    }
  }

  async function loadDetail(target: string) {
    controller?.abort();
    controller = new AbortController();
    detailError = null;
    try {
      const next = await getAdaptation(target, controller.signal);
      if (target === id) {
        detail = next;
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return;
      }
      detailError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    load();
  });

  $effect(() => {
    const target = id;
    untrack(() => {
      detail = null;
      detailError = null;
      if (target) {
        loadDetail(target);
      }
    });
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

  $effect(() => {
    if (wide && loaded && !id && plans.length > 0) {
      goto(hrefFor(plans[0].id), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  const off = live.on("adaptation.created", () => load());
  onDestroy(() => {
    off();
    controller?.abort();
  });

  const week = $derived(
    plans.filter((p) => Date.now() - new Date(p.created_at).getTime() < WEEK)
      .length
  );

  const place = (p: { place: string; powiat: string | null }) =>
    [p.place, p.powiat ? powiatName(p.powiat, powiats.names) : ""]
      .filter(Boolean)
      .join(", ");

  function move(step: number) {
    if (plans.length === 0) {
      return;
    }
    const index = plans.findIndex((p) => p.id === id);
    const next = plans[Math.max(0, Math.min(plans.length - 1, index + step))];
    goto(hrefFor(next.id), { noScroll: true, replaceState: true });
  }

  function keydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (
      target.closest("input, textarea, select, [contenteditable]") ||
      event.metaKey ||
      event.ctrlKey ||
      event.altKey
    ) {
      return;
    }
    const step: Record<string, number> = {
      ArrowDown: 1,
      ArrowUp: -1,
      j: 1,
      k: -1,
    };
    if (event.key in step) {
      event.preventDefault();
      move(step[event.key]);
    }
  }

  const lists: {
    key: "steps" | "staff" | "partners" | "cost_drivers" | "measures";
    title: string;
  }[] = [
    { key: "steps", title: "Jak zacząć" },
    { key: "staff", title: "Kogo potrzebujecie" },
    { key: "partners", title: "Z kim współpracować" },
    { key: "cost_drivers", title: "Od czego zależy koszt" },
    { key: "measures", title: "Co mierzyć" },
  ];

  const facts = $derived(detail?.plan.local_facts ?? []);
  const challenges = $derived(detail?.plan.regional_challenges ?? []);
  function figure(f: { unit?: string | null; value: number | string }) {
    const value =
      typeof f.value === "number" ? f.value.toLocaleString("pl-PL") : f.value;
    if (!f.unit) {
      return value;
    }
    return f.unit === "%" ? `${value}%` : `${value} ${f.unit}`;
  }
</script>

<svelte:head>
  <title>Plany wdrożenia · HubMi</title>
</svelte:head>

<svelte:window onkeydown={keydown} />

<div class={["binder", id && "has-item"]}>
  <main class="board">
    <header class="bhead">
      <div class="min-w-0">
        <h1
          class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
        >
          Plany wdrożenia
        </h1>
        <p class="mt-1.5 max-w-[70ch] text-pretty text-hm-ink-soft text-sm">
          Instytucje z&nbsp;Małopolski, które zamówiły plan wdrożenia innowacji
          u&nbsp;siebie. Plan pisze model z&nbsp;opisu innowacji i&nbsp;danych
          ROPS o&nbsp;powiecie; tu widać, kto chce czego i&nbsp;gdzie.
        </p>
      </div>
      <dl class="stats">
        <div>
          <dt>planów od początku</dt>
          <dd class="tabular">{Math.max(total, plans.length)}</dd>
        </div>
        <div>
          <dt>w&nbsp;tym tygodniu</dt>
          <dd class="tabular">+{week}</dd>
        </div>
      </dl>
    </header>

    <div class="work">
      <section aria-label="Plany wdrożenia" class="register">
        <div class="rhead">
          <span>Instytucja i&nbsp;miejsce</span>
          <span>Innowacja</span>
        </div>
        {#if loadError && !loaded}
          <ErrorState error={loadError} retry={load} />
        {:else if !loaded}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if plans.length === 0}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">
            Nikt jeszcze nie zamówił planu wdrożenia. Plany pojawią się tu same,
            gdy instytucja użyje "Wdróż u siebie" na stronie innowacji.
          </p>
        {:else}
          <ol aria-label="Lista planów" class="rows">
            {#each plans as p (p.id)}
              <li>
                <a
                  aria-current={p.id === id ? "true" : undefined}
                  class="row"
                  data-sveltekit-noscroll
                  data-sveltekit-replacestate
                  href={hrefFor(p.id)}
                >
                  <span class="grid min-w-0 gap-[3px]">
                    <span class="tx">{p.institution.name}, {place(p)}</span>
                    <span class="text-hm-ink-soft text-xs tabular"
                      >{when(p.created_at)}
                      · {nbsp(p.service_name)}</span
                    >
                  </span>
                  <span class="inn">{p.innovation.title}</span>
                </a>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      {#if id}
        <article aria-labelledby="plan-title" class="sheet">
          <a class="back" href={hrefFor(null)}>
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
              <path d="m15 18-6-6 6-6" />
            </svg>
            Plany wdrożenia
          </a>
          {#if detailError}
            <ErrorState error={detailError} retry={() => loadDetail(id)} />
          {:else if !detail}
            <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
          {:else}
            <div class="grid max-w-[680px] gap-[22px]">
              <header class="grid gap-2">
                <p class="text-[13px] text-hm-ink-soft">
                  Zamówienie z&nbsp;{dayWords(detail.created_at)}
                  ·
                  <span class="ai">plan napisany przez model</span>
                </p>
                <h2
                  class="text-balance font-semibold text-[22px] tracking-tight"
                  id="plan-title"
                >
                  {detail.plan.service_name}
                </h2>
                <dl class="who">
                  <div>
                    <dt>Kto</dt>
                    <dd>{detail.institution.name}, {detail.place}</dd>
                  </div>
                  <div>
                    <dt>Powiat</dt>
                    <dd>
                      {detail.powiat ? powiatName(detail.powiat, powiats.names) : "nie podano"}
                    </dd>
                  </div>
                  <div>
                    <dt>Innowacja</dt>
                    <dd>
                      <a
                        class="link"
                        href="{resolve('/library')}/{detail.innovation.slug}"
                        >{detail.innovation.title}</a
                      >
                    </dd>
                  </div>
                  <div>
                    <dt>Link dla instytucji</dt>
                    <dd>
                      <a
                        class="link"
                        href={detail.share_path}
                        rel="noreferrer"
                        target="_blank"
                        >strona planu</a
                      >
                    </dd>
                  </div>
                </dl>
              </header>

              <section aria-labelledby="ctx-h">
                <h3 class="h3" id="ctx-h">Co napisała instytucja</h3>
                <p class="quote">{nbsp(detail.context)}</p>
              </section>

              <section aria-labelledby="sum-h">
                <h3 class="h3" id="sum-h">Usługa</h3>
                <p class="text-pretty text-sm leading-relaxed">
                  {nbsp(detail.plan.summary)}
                </p>
                <h3 class="h3 mt-3" id="who-h">Dla kogo</h3>
                <p class="text-pretty text-sm leading-relaxed">
                  {nbsp(detail.plan.target_group)}
                </p>
              </section>

              {#if detail.plan.local_context || facts.length > 0}
                <section aria-labelledby="loc-h">
                  <h3 class="h3" id="loc-h">Dane ROPS o&nbsp;powiecie</h3>
                  {#if detail.plan.local_context}
                    <p class="text-pretty text-sm leading-relaxed">
                      {nbsp(detail.plan.local_context)}
                    </p>
                  {/if}
                  {#if facts.length > 0}
                    <ul class="facts">
                      {#each facts as f (f.label)}
                        <li>
                          <b class="tabular">{figure(f)}</b>
                          <span>
                            {f.label}{f.year ? `, ${f.year}` : ""}{f.region_value !== null && f.region_value !== undefined ? `, Małopolska ${figure({ unit: f.unit, value: f.region_value })}` : ""}
                            {#if f.source_url}
                              ·
                              <a
                                class="link"
                                href={f.source_url}
                                rel="noreferrer"
                                target="_blank"
                                >{f.source_title ?? "źródło"}{f.page ? `, s. ${f.page}` : ""}</a
                              >
                            {/if}
                          </span>
                        </li>
                      {/each}
                    </ul>
                  {/if}
                </section>
              {/if}

              {#each lists as l (l.key)}
                {#if detail.plan[l.key].length > 0}
                  <section aria-labelledby="l-{l.key}">
                    <h3 class="h3" id="l-{l.key}">{l.title}</h3>
                    <ol class={["plan", l.key === "steps" && "steps"]}>
                      {#each detail.plan[l.key] as item, i (i)}
                        <li>
                          {#if typeof item === "string"}
                            {nbsp(item)}
                          {:else}
                            <b>{item.title}</b>
                            <span class="block text-hm-ink-soft"
                              >{nbsp(item.description)}</span
                            >
                          {/if}
                        </li>
                      {/each}
                    </ol>
                  </section>
                {/if}
              {/each}

              {#if detail.plan.risks.length > 0}
                <section aria-labelledby="risk-h">
                  <h3 class="h3" id="risk-h">Ryzyka</h3>
                  <ol class="plan">
                    {#each detail.plan.risks as r, i (i)}
                      <li>
                        <b>{r.risk}</b>
                        <span class="block text-hm-ink-soft"
                          >{nbsp(r.mitigation)}</span
                        >
                      </li>
                    {/each}
                  </ol>
                </section>
              {/if}

              {#if detail.plan.combine.length > 0}
                <section aria-labelledby="comb-h">
                  <h3 class="h3" id="comb-h">
                    Połącz z&nbsp;innymi innowacjami
                  </h3>
                  <ol class="plan">
                    {#each detail.plan.combine as c (c.slug)}
                      <li>
                        <a class="link" href="{resolve('/library')}/{c.slug}"
                          >{c.title}</a
                        >
                        <span class="block text-hm-ink-soft"
                          >{nbsp(c.why)}</span
                        >
                      </li>
                    {/each}
                  </ol>
                </section>
              {/if}

              {#if challenges.length > 0}
                <section aria-labelledby="ch-h">
                  <h3 class="h3" id="ch-h">Powiązane wyzwania regionu</h3>
                  <ol class="plan">
                    {#each challenges as c (c.slug)}
                      <li>
                        <a
                          class="link"
                          href={resolve("/knowledge/[[id]]", { id: c.slug })}
                          >{c.title}</a
                        >
                        {#if c.summary}
                          <span class="block text-hm-ink-soft"
                            >{nbsp(c.summary)}</span
                          >
                        {/if}
                      </li>
                    {/each}
                  </ol>
                </section>
              {/if}

              {#if detail.plan.to_check.length > 0}
                <section aria-labelledby="chk-h">
                  <h3 class="h3" id="chk-h">Do sprawdzenia u&nbsp;siebie</h3>
                  <ol class="plan">
                    {#each detail.plan.to_check as t, i (i)}
                      <li>{nbsp(t)}</li>
                    {/each}
                  </ol>
                </section>
              {/if}
            </div>
          {/if}
        </article>
      {:else if wide}
        <div class="empty">
          <p class="text-hm-ink-soft text-sm">
            {plans.length === 0 ? "Brak planów." : `Wybierz plan z listy: ${plans.length} ${plural(plans.length, "plan", "plany", "planów")}.`}
          </p>
        </div>
      {/if}
    </div>
  </main>
</div>

<style>
  .binder {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    min-height: 0;
    padding: 0 18px 18px;
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

  .bhead {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 32px;
    align-items: end;
  }

  .stats {
    display: flex;
    gap: 28px;
    align-items: end;
    margin: 0;
  }

  .stats div {
    display: flex;
    flex-direction: column-reverse;
    gap: 3px;
  }

  .stats dt {
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
  }

  .stats dd {
    margin: 0;
    font-size: 26px;
    font-weight: 650;
    line-height: 1;
    letter-spacing: -0.03em;
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
    display: grid;
    grid-template-columns: minmax(0, 1fr) 160px;
    gap: 12px;
    align-items: center;
    min-height: 40px;
    padding: 4px 12px 4px 8px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    border-bottom: 1px solid var(--hm-rule);
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
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 160px;
    gap: 12px;
    align-items: baseline;
    min-height: 64px;
    padding: 11px 12px 11px 8px;
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

  .tx {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 13.5px;
    font-weight: 560;
    line-height: 1.42;
  }

  .inn {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 12.5px;
    line-height: 1.4;
    color: var(--hm-ink-soft);
  }

  .sheet {
    position: relative;
    min-height: 0;
    padding: 26px 30px 30px;
    overflow: auto;
    overscroll-behavior: contain;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: var(--hm-raised);
  }

  .back {
    display: none;
  }

  .empty {
    display: grid;
    place-items: center;
    border: 1px dashed var(--hm-rule);
    border-radius: 20px;
  }

  .ai {
    display: inline-flex;
    gap: 5px;
    align-items: center;
  }

  .ai::before {
    display: inline-flex;
    align-items: center;
    height: 16px;
    padding: 0 5px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: 0.08em;
    content: "AI";
    border: 1px solid currentColor;
    border-radius: 4px;
  }

  .who {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 20px;
    padding: 12px 14px;
    margin: 4px 0 0;
    font-size: 13px;
    background: var(--hm-sunk);
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .who dt {
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .who dd {
    margin: 2px 0 0;
    font-weight: 560;
  }

  .h3 {
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 650;
  }

  .quote {
    padding-left: 12px;
    font-size: 14px;
    line-height: 1.5;
    text-wrap: pretty;
    border-left: 2px solid var(--hm-rule);
  }

  .link {
    text-decoration: underline;
    text-decoration-color: var(--hm-rule);
    text-underline-offset: 3px;
  }

  .link:hover {
    color: var(--hm-stamp);
    text-decoration-color: currentColor;
  }

  .facts {
    display: grid;
    gap: 6px;
    padding: 0;
    margin: 8px 0 0;
    font-size: 13px;
    list-style: none;
  }

  .facts li {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 10px;
    align-items: baseline;
  }

  .facts b {
    font-size: 15px;
    font-weight: 650;
  }

  .plan {
    display: grid;
    gap: 8px;
    padding: 0;
    margin: 0;
    font-size: 14px;
    line-height: 1.45;
    list-style: none;
  }

  .plan li {
    position: relative;
    padding-left: 16px;
  }

  .plan li::before {
    position: absolute;
    top: 9px;
    left: 2px;
    width: 5px;
    height: 5px;
    content: "";
    background: var(--hm-stamp);
    border-radius: 50%;
  }

  .plan.steps {
    counter-reset: step;
  }

  .plan.steps li {
    padding-left: 30px;
  }

  .plan.steps li::before {
    top: 0;
    left: 0;
    width: auto;
    height: auto;
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-stamp);
    content: counter(step);
    counter-increment: step;
    background: none;
  }

  @media (max-width: 899px) {
    .binder {
      padding: 0 10px 10px;
    }

    .board {
      padding: 16px 12px 12px;
      border-radius: 22px;
    }

    .bhead {
      grid-template-columns: minmax(0, 1fr);
    }

    .work {
      grid-template-columns: minmax(0, 1fr);
    }

    .rhead,
    .row {
      grid-template-columns: minmax(0, 1fr);
    }

    .rhead span:last-child {
      display: none;
    }

    .has-item .register,
    .has-item .bhead {
      display: none;
    }

    .has-item .board {
      padding: 0;
      background: none;
      border-radius: 22px;
      box-shadow: none;
    }

    .sheet {
      padding: 16px;
      border-radius: 18px;
    }

    .back {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      min-height: 44px;
      padding: 0 10px 0 4px;
      margin-bottom: 12px;
      font-size: 14px;
      font-weight: 500;
      border-radius: 10px;
    }

    .who {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
