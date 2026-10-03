<script lang="ts">
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminNeed,
    mergeCluster,
    type NeedStatus,
    refreshCluster,
    setNeedStatus,
    splitCluster,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import ContextMenu from "$lib/components/hub/context-menu.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import NeedSheet from "$lib/components/hub/need-sheet.svelte";
  import Register from "$lib/components/hub/register.svelte";
  import Sparkline from "$lib/components/hub/sparkline.svelte";
  import type { FolderTab } from "$lib/components/hub/types";
  import { plural, registerNumber } from "$lib/format";
  import { inbox } from "$lib/live/inbox.svelte";

  const WEEK = 7 * 86_400_000;

  let menu = $state<ContextMenu | null>(null);
  let sheet = $state<NeedSheet | null>(null);
  let wide = $state(true);

  const id = $derived(page.params.id ?? null);
  const folder = $derived(page.url.searchParams.get("folder") ?? "all");
  const waiting = $derived(page.url.searchParams.get("status") === "new");

  function href(
    needId: string | null,
    next: { folder?: string; waiting?: boolean } = {}
  ) {
    const params = new URLSearchParams();
    const f = next.folder ?? folder;
    const w = next.waiting ?? waiting;
    if (f !== "all") {
      params.set("folder", f);
    }
    if (w) {
      params.set("status", "new");
    }
    const query = params.toString();
    const path = needId
      ? resolve("/needs/[[id]]", { id: needId })
      : resolve("/needs/[[id]]", {});
    return `${path}${query ? `?${query}` : ""}`;
  }

  const recent = (iso: string) => Date.now() - new Date(iso).getTime() < WEEK;

  const folders = $derived.by(() => {
    if (inbox.clusters.length > 0) {
      return inbox.clusters.map((c) => ({
        cluster: c,
        id: c.id,
        size: c.size,
        title: c.title,
        week: c.new_last_7d,
      }));
    }
    const seen = new Map<
      string,
      { id: string; title: string; size: number; week: number; cluster: null }
    >();
    for (const n of inbox.needs) {
      if (n.cluster && !seen.has(n.cluster.id)) {
        seen.set(n.cluster.id, {
          cluster: null,
          id: n.cluster.id,
          size: n.cluster.size,
          title: n.cluster.title,
          week: 0,
        });
      }
    }
    for (const n of inbox.needs) {
      const f = n.cluster ? seen.get(n.cluster.id) : undefined;
      if (f && recent(n.created_at)) {
        f.week += 1;
      }
    }
    return [...seen.values()];
  });

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: inbox.needs.filter((n) => inbox.unopened(n)).length,
      href: href(null, { folder: "all" }),
      id: "all",
      size: Math.max(inbox.total, inbox.needs.length),
      title: "Wszystkie potrzeby",
      week: inbox.needs.filter((n) => recent(n.created_at)).length,
    },
    ...[...folders]
      .sort((a, b) => b.size - a.size || a.title.localeCompare(b.title, "pl"))
      .map((f) => ({
        ...f,
        fresh: inbox.needs.filter(
          (n) => n.cluster?.id === f.id && inbox.unopened(n)
        ).length,
        href: href(null, { folder: f.id }),
      })),
  ]);

  const currentFolder = $derived(folders.find((f) => f.id === folder) ?? null);

  const visible = $derived(
    inbox.needs.filter(
      (n) =>
        (folder === "all" || n.cluster?.id === folder) &&
        (!waiting || n.status === "new")
    )
  );

  const counts = $derived({
    answered: inbox.needs.filter((n) => n.status === "answered").length,
    fresh: inbox.needs.filter((n) => n.status === "new").length,
  });

  $effect(() => {
    const query = matchMedia("(min-width: 900px)");
    wide = query.matches;
    const update = () => {
      wide = query.matches;
    };
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  });

  $effect(() => {
    if (wide && !id && visible.length > 0) {
      goto(href(visible[0].id), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  function move(step: number) {
    if (visible.length === 0) {
      return;
    }
    const index = visible.findIndex((n) => n.id === id);
    const next =
      visible[Math.max(0, Math.min(visible.length - 1, index + step))];
    goto(href(next.id), { noScroll: true, replaceState: true }).then(() => {
      document
        .querySelector<HTMLElement>(`.row[data-id="${next.id}"]`)
        ?.focus();
    });
  }

  function flip(step: number) {
    const index = tabs.findIndex((t) => t.id === folder);
    const next = tabs[Math.max(0, Math.min(tabs.length - 1, index + step))];
    goto(next.href, { noScroll: true, replaceState: true });
  }

  function keydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    rowKeys(event);
    if (
      target.closest("input, textarea, select, [contenteditable]") ||
      event.metaKey ||
      event.ctrlKey ||
      event.altKey
    ) {
      return;
    }
    const actions: Record<string, () => void> = {
      "[": () => flip(-1),
      "]": () => flip(1),
      ArrowDown: () => move(1),
      ArrowUp: () => move(-1),
      e: () => sheet?.pressStatus("closed"),
      j: () => move(1),
      k: () => move(-1),
      r: () => sheet?.focusReply(),
    };
    const action = actions[event.key];
    if (action && !target.closest('[role="menu"]')) {
      event.preventDefault();
      action();
    }
  }

  async function quickStatus(
    need: AdminNeed,
    status: NeedStatus,
    anchor: HTMLElement | null
  ) {
    const before = need.status;
    inbox.patch({ id: need.id, status });
    try {
      inbox.patch(await setNeedStatus(need.id, status));
    } catch (e) {
      inbox.patch({ id: need.id, status: before });
      const { showTip } = await import("$lib/tip");
      showTip(
        anchor,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
    }
  }

  function rowMenu(
    need: AdminNeed,
    event: MouseEvent | KeyboardEvent,
    row?: HTMLElement
  ) {
    const anchor = row ?? (event.currentTarget as HTMLElement);
    menu?.show(
      event,
      [
        {
          hint: "Enter",
          label: "Otwórz",
          run: () =>
            goto(href(need.id), { noScroll: true, replaceState: true }),
        },
        {
          hint: "R",
          label: "Odpowiedz",
          run: () =>
            goto(href(need.id), { noScroll: true, replaceState: true }).then(
              () => setTimeout(() => sheet?.focusReply(), 50)
            ),
        },
        "-",
        ...(need.status === "answered"
          ? []
          : [
              {
                label: "Oznacz jako odpowiedzianą",
                run: () => quickStatus(need, "answered", anchor),
              },
            ]),
        ...(need.status === "new"
          ? []
          : [
              {
                label: "Oznacz jako nową",
                run: () => quickStatus(need, "new", anchor),
              },
            ]),
        ...(need.status === "closed"
          ? []
          : [
              {
                hint: "E",
                label: "Zamknij",
                run: () => quickStatus(need, "closed", anchor),
              },
            ]),
        ...(need.cluster && need.cluster.size > 1
          ? [
              {
                label: "Wydziel do nowej teczki",
                run: () =>
                  clusterAction(async () => {
                    const { cluster } = need;
                    if (!cluster) {
                      return null;
                    }
                    const result = await splitCluster(cluster.id, [need.id]);
                    return result.created.id;
                  }, anchor),
              },
            ]
          : []),
        "-",
        {
          label: "Kopiuj link",
          run: () =>
            navigator.clipboard?.writeText(
              new URL(
                resolve("/needs/[[id]]", { id: need.id }),
                location.origin
              ).toString()
            ),
        },
      ],
      anchor
    );
  }

  async function clusterAction(
    run: () => Promise<string | null>,
    anchor: HTMLElement | null
  ) {
    const { showTip } = await import("$lib/tip");
    try {
      const target = await run();
      await inbox.refresh();
      if (target) {
        await goto(href(null, { folder: target }), {
          noScroll: true,
          replaceState: true,
        });
      }
    } catch (e) {
      showTip(
        anchor,
        e instanceof ApiError ? e.message : "Nie udało się.",
        "bad"
      );
    }
  }

  function folderMenu(tab: FolderTab, event: MouseEvent) {
    if (!tab.cluster && tab.id === "all") {
      return;
    }
    const anchor = event.currentTarget as HTMLElement;
    const others = tabs
      .filter((t) => t.id !== "all" && t.id !== tab.id)
      .slice(0, 8);
    menu?.show(
      event,
      [
        {
          label: "Otwórz",
          run: () => goto(tab.href, { noScroll: true, replaceState: true }),
        },
        {
          label: "Odśwież opis",
          run: () =>
            clusterAction(async () => {
              await refreshCluster(tab.id);
              return null;
            }, anchor),
        },
        ...(others.length > 0 ? ["-" as const] : []),
        ...others.map((o) => ({
          label: `Scal z: ${o.title}`,
          run: () =>
            clusterAction(async () => {
              const into = await mergeCluster(tab.id, o.id);
              return into.id;
            }, anchor),
        })),
      ],
      anchor
    );
  }

  function rowKeys(event: KeyboardEvent) {
    const row = (event.target as HTMLElement).closest<HTMLElement>(".row");
    if (
      row &&
      (event.key === "ContextMenu" || (event.shiftKey && event.key === "F10"))
    ) {
      const need = inbox.needs.find((n) => n.id === row.dataset.id);
      if (need) {
        rowMenu(need, event, row);
      }
    }
  }

  const title = $derived.by(() => {
    const n = inbox.needs.find((x) => x.id === id);
    return n?.number
      ? `Potrzeba nr ${registerNumber(n.number)} · HubMi`
      : "Dziennik potrzeb · HubMi";
  });
</script>

<svelte:head>
  <title>{title}</title>
</svelte:head>

<svelte:window onkeydown={keydown} />

<div class={["binder", id && "has-need"]}>
  <nav aria-label="Teczki" class="rail">
    <FolderTabs current={folder} oncontext={folderMenu} {tabs} />
  </nav>

  <main class={["board", folder === "all" && "first"]}>
    <header class="bhead">
      <div class="min-w-0">
        <h1
          class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
        >
          {currentFolder?.title ?? "Dziennik potrzeb"}
        </h1>
        <p class="mt-1.5 max-w-[70ch] text-pretty text-hm-ink-soft text-sm">
          {#if currentFolder?.cluster?.summary}
            {currentFolder.cluster.summary}
            {#if currentFolder.cluster.powiats && currentFolder.cluster.powiats.length > 0}
              <span class="mt-1 block text-[13px]">
                Najczęściej:
                {currentFolder.cluster.powiats.map((p) => `${p.name} (${p.count})`).join(", ")}
              </span>
            {/if}
          {:else if !currentFolder}
            {counts.fresh}
            {plural(counts.fresh, "czeka", "czekają", "czeka")}
            na odpowiedź,
            {counts.answered}
            z&nbsp;odpowiedzią.
          {/if}
        </p>
      </div>
      <dl class="stats">
        <div>
          <dt>potrzeb</dt>
          <dd class="tabular">
            {currentFolder ? currentFolder.size : Math.max(inbox.total, inbox.needs.length)}
          </dd>
        </div>
        <div>
          <dt>w&nbsp;tym tygodniu</dt>
          <dd class="tabular">
            +{tabs.find((t) => t.id === folder)?.week ?? 0}
          </dd>
        </div>
        {#if (currentFolder?.cluster?.ideas_count ?? 0) > 0}
          <div>
            <dt>
              {plural(currentFolder?.cluster?.ideas_count ?? 0, "pomysł", "pomysły", "pomysłów")}
            </dt>
            <dd class="tabular">
              <a
                class="ideas-link"
                href="{resolve('/ideas/[[id]]', {})}?problem={currentFolder?.id}"
                >{currentFolder?.cluster?.ideas_count}</a
              >
            </dd>
          </div>
        {/if}
        {#if currentFolder?.cluster?.daily && currentFolder.cluster.daily.length > 1}
          <div>
            <dt>ostatnie 14 dni</dt>
            <dd><Sparkline values={currentFolder.cluster.daily} /></dd>
          </div>
        {/if}
      </dl>
    </header>

    <div class="work">
      <section aria-label="Dziennik" class="register">
        <div class="rhead">
          <span class="pl-2">Nr</span>
          <span>Treść</span>
          <nav aria-label="Filtr" class="filter">
            <a
              aria-current={waiting ? undefined : "true"}
              data-sveltekit-noscroll
              data-sveltekit-replacestate
              href={href(id, { waiting: false })}
              >Wszystkie</a
            >
            <a
              aria-current={waiting ? "true" : undefined}
              data-sveltekit-noscroll
              data-sveltekit-replacestate
              href={href(id, { waiting: true })}
              >Czekają</a
            >
          </nav>
        </div>
        {#if inbox.needsError && inbox.needs.length === 0}
          <ErrorState error={inbox.needsError} retry={() => inbox.refresh()} />
        {:else if !inbox.loaded}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if visible.length === 0}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">
            {#if waiting}
              Nic nie czeka na odpowiedź.
            {:else if inbox.needs.length === 0}
              Nie ma jeszcze żadnych potrzeb. Pojawią się tutaj same, gdy ktoś
              opisze problem w&nbsp;aplikacji.
            {:else}
              W tej teczce nie ma potrzeb.
            {/if}
          </p>
        {:else}
          <Register
            current={id}
            hrefFor={(n) => href(n.id)}
            needs={visible}
            oncontext={rowMenu}
            showFolder={folder === "all"}
          />
        {/if}
      </section>

      {#if id}
        <NeedSheet backHref={href(null)} {folder} {id} bind:this={sheet} />
      {:else if wide}
        <div class="empty">
          <p class="text-hm-ink-soft text-sm">
            Wybierz potrzebę z&nbsp;dziennika.
          </p>
        </div>
      {/if}
    </div>
  </main>
</div>

<ContextMenu bind:this={menu} />

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

  .ideas-link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 4px;
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
    grid-template-columns: 50px minmax(0, 1fr) auto;
    gap: 12px;
    align-items: center;
    min-height: 40px;
    padding: 4px 0 4px 4px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    border-bottom: 1px solid var(--hm-rule);
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
    height: 28px;
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

    .has-need .register,
    .has-need .bhead,
    .has-need .rail {
      display: none;
    }

    .has-need .board {
      padding: 0;
      background: none;
      border-radius: 22px;
      box-shadow: none;
    }

    .filter a {
      height: 36px;
    }
  }
</style>
