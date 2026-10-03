<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminVolunteer,
    listVolunteers,
    type VolunteerCounts,
    type VolunteerStatus,
    volunteerCounts,
  } from "$lib/api/admin";
  import ErrorState from "$lib/components/error-state.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import type { FolderTab } from "$lib/components/hub/types";
  import VolunteerSheet from "$lib/components/hub/volunteer-sheet.svelte";
  import { plural, when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import { fold, whoLabel } from "$lib/opinions";
  import { volunteerLabel, volunteerStatuses } from "$lib/volunteers";

  let rows = $state<AdminVolunteer[]>([]);
  let counts = $state<VolunteerCounts | null>(null);
  let loaded = $state(false);
  let loadError = $state<Error | null>(null);
  let wide = $state(true);
  let query = $state("");
  let typing: ReturnType<typeof setTimeout> | undefined;

  const id = $derived(page.params.id ?? null);
  const params = $derived(page.url.searchParams);
  const group = $derived<VolunteerStatus | "all">(
    volunteerStatuses.find((s) => s.id === params.get("status"))?.id ?? "all"
  );
  const innovation = $derived(params.get("innovation"));
  const q = $derived(params.get("q") ?? "");

  $effect(() => {
    const next = q;
    untrack(() => {
      if (fold(next) !== fold(query)) {
        query = next;
      }
    });
  });

  function href(
    target: string | null,
    next: {
      group?: VolunteerStatus | "all";
      innovation?: string | null;
      q?: string;
    } = {}
  ) {
    const out = new URLSearchParams();
    const g = next.group ?? group;
    const inn = next.innovation === undefined ? innovation : next.innovation;
    const text = next.q ?? q;
    if (g !== "all") {
      out.set("status", g);
    }
    if (inn) {
      out.set("innovation", inn);
    }
    if (text) {
      out.set("q", text);
    }
    const path = target
      ? resolve("/volunteers/[[id]]", { id: target })
      : resolve("/volunteers/[[id]]", {});
    const s = out.toString();
    return s ? `${path}?${s}` : path;
  }

  async function load() {
    try {
      const [items, c] = await Promise.all([
        listVolunteers(),
        volunteerCounts().catch(() => null),
      ]);
      rows = items;
      counts = c;
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
    live.on("volunteer.created", load),
    live.on("volunteer.updated", load),
    live.on("volunteer.reported", load),
    live.onReconnect(load),
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

  const countOf = (status: VolunteerStatus) =>
    counts?.[status] ?? rows.filter((r) => r.status === status).length;

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: 0,
      href: href(null, { group: "all" }),
      id: "all",
      note:
        countOf("new") > 0
          ? `${countOf("new")} ${plural(countOf("new"), "czeka", "czekają", "czeka")}`
          : undefined,
      size: rows.length,
      title: "Wszystkie zgłoszenia",
      week: 0,
    },
    ...volunteerStatuses.map((s) => ({
      cluster: null,
      fresh: 0,
      href: href(null, { group: s.id }),
      id: s.id,
      size: countOf(s.id),
      title: s.label,
      week: 0,
    })),
  ]);

  const innovationTitle = $derived(
    innovation
      ? (rows.find((r) => r.innovation.slug === innovation)?.innovation.title ??
          innovation)
      : null
  );

  const visible = $derived(
    rows.filter((r) => {
      if (group !== "all" && r.status !== group) {
        return false;
      }
      if (innovation && r.innovation.slug !== innovation) {
        return false;
      }
      if (!q) {
        return true;
      }
      const hay = fold(
        [
          r.email,
          r.organization ?? "",
          r.innovation.title,
          r.powiat_name,
          r.proposal,
        ].join(" ")
      );
      return hay.includes(fold(q));
    })
  );

  $effect(() => {
    if (wide && loaded && !id && visible.length > 0) {
      goto(href(visible[0].id), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  function search(value: string) {
    query = value;
    if (typing) {
      clearTimeout(typing);
    }
    typing = setTimeout(() => {
      goto(href(id, { q: value.trim() }), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }, 250);
  }

  function changed(next: AdminVolunteer) {
    rows = rows.map((r) => (r.id === next.id ? { ...r, ...next } : r));
    volunteerCounts()
      .then((c) => {
        counts = c;
      })
      .catch(() => undefined);
  }

  function move(step: number) {
    if (visible.length === 0) {
      return;
    }
    const index = visible.findIndex((r) => r.id === id);
    const next =
      visible[Math.max(0, Math.min(visible.length - 1, index + step))];
    goto(href(next.id), { noScroll: true, replaceState: true });
  }

  function keydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (
      target.closest("input, textarea, select, [contenteditable]") ||
      event.metaKey ||
      event.ctrlKey ||
      event.altKey
    ) {
      if (event.key === "Escape" && target.id === "volunteers-search") {
        search("");
      }
      return;
    }
    if (event.key === "/") {
      event.preventDefault();
      document.getElementById("volunteers-search")?.focus();
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

  const title = $derived(
    group === "all"
      ? "Wolontariusze"
      : `Wolontariusze: ${volunteerLabel[group].toLocaleLowerCase("pl")}`
  );
</script>

<svelte:head>
  <title>Wolontariusze · HubMi</title>
</svelte:head>

<svelte:window onkeydown={keydown} />

<div class={["binder", id && "has-item"]}>
  <nav aria-label="Stan zgłoszeń" class="rail">
    <FolderTabs current={group} {tabs} />
  </nav>

  <main class={["board", group === "all" && "first"]}>
    <header class="bhead">
      <div class="min-w-0">
        <h1
          class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
        >
          {title}
        </h1>
        <p class="mt-1.5 max-w-[70ch] text-pretty text-hm-ink-soft text-sm">
          {#if innovation}
            Zgłoszenia do innowacji
            <b class="font-semibold text-hm-ink">{innovationTitle}</b>
            ·
            <a class="clear" href={href(null, { innovation: null })}
              >pokaż wszystkie</a
            >
          {:else}
            Osoby, które chcą sprawdzić innowację u&nbsp;siebie. Każde
            zgłoszenie czyta pracownik ROPS: pisze, przyjmuje albo odrzuca.
            Przyjęta osoba dostaje link do formularza raportu.
          {/if}
        </p>
      </div>
    </header>

    <div class="work">
      <section aria-label="Zgłoszenia wolontariuszy" class="register">
        <div class="rhead">
          <label class="search">
            <span class="sr-only">Szukaj osoby, organizacji lub innowacji</span>
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
              autocomplete="off"
              id="volunteers-search"
              oninput={(event) => search(event.currentTarget.value)}
              placeholder="Szukaj osoby, organizacji lub innowacji"
              type="search"
              value={query}
            >
            <kbd aria-hidden="true" class="max-[899px]:hidden">/</kbd>
          </label>
          <span aria-live="polite" class="total tabular">
            {visible.length}
            {plural(visible.length, "zgłoszenie", "zgłoszenia", "zgłoszeń")}
          </span>
        </div>
        <div class="scroll">
          {#if loadError && !loaded}
            <ErrorState error={loadError} retry={load} />
          {:else if !loaded}
            <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
          {:else if visible.length === 0}
            <p class="px-3 py-6 text-hm-ink-soft text-sm">
              {rows.length === 0 ? "Nikt jeszcze nie zgłosił się jako wolontariusz. Zgłoszenia pojawią się tu same." : "Brak zgłoszeń w tym widoku."}
            </p>
          {:else}
            <ol class="rows">
              {#each visible as r (r.id)}
                <li>
                  <a
                    aria-current={r.id === id ? "true" : undefined}
                    class={["row", `is-${r.status}`]}
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href(r.id)}
                  >
                    <span class="grid min-w-0 gap-[3px]">
                      <span class="font-semibold text-sm"
                        >{r.organization || r.email}</span
                      >
                      <span class="text-sm">{r.innovation.title}</span>
                      <span class="text-hm-ink-soft text-xs">
                        {whoLabel[r.who]}
                        · {r.powiat_name} · {when(r.created_at)}
                      </span>
                    </span>
                    <span class="st">{volunteerLabel[r.status]}</span>
                  </a>
                </li>
              {/each}
            </ol>
          {/if}
        </div>
      </section>

      {#if id}
        <VolunteerSheet backHref={href(null)} {id} onchange={changed} />
      {:else if wide}
        <div class="empty">
          <p class="text-hm-ink-soft text-sm">
            Wybierz zgłoszenie z&nbsp;listy.
          </p>
        </div>
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
    gap: 8px 32px;
    align-items: end;
  }

  .clear {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
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
    flex-wrap: wrap;
    gap: 8px 12px;
    align-items: center;
    justify-content: space-between;
    min-height: 44px;
    padding: 6px 0 6px 4px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    border-bottom: 1px solid var(--hm-rule);
  }

  .search {
    display: flex;
    flex: 1 1 220px;
    gap: 8px;
    align-items: center;
    min-width: 0;
    height: 32px;
    padding: 0 8px 0 10px;
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
    flex: 1;
    min-width: 0;
    font-size: 13px;
    color: var(--hm-ink);
    outline: none;
    background: none;
    border: 0;
  }

  .search input::placeholder {
    color: var(--hm-ink-soft);
  }

  .search kbd {
    padding: 2px 5px;
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--hm-board);
    border-radius: 5px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .total {
    white-space: nowrap;
  }

  .scroll {
    position: relative;
    min-height: 0;
    overflow: auto;
  }

  .rows {
    padding: 0 0 8px;
    margin: 0;
    list-style: none;
  }

  .row {
    position: relative;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 120px;
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

  .st {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
  }

  .st::before {
    width: 6px;
    height: 6px;
    content: "";
    background: currentColor;
    border-radius: 50%;
  }

  .is-new .st {
    color: var(--hm-stamp);
  }

  .is-accepted .st,
  .is-reported .st {
    color: var(--hm-ok);
  }

  .is-rejected .st {
    color: var(--hm-bad);
  }

  .empty {
    display: grid;
    place-items: center;
    border: 1px dashed var(--hm-rule);
    border-radius: 20px;
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

    .bhead {
      grid-template-columns: minmax(0, 1fr);
    }

    .work {
      grid-template-columns: minmax(0, 1fr);
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
      border-radius: 22px;
      box-shadow: none;
    }
  }
</style>
