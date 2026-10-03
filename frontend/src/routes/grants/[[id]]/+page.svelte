<script lang="ts">
  import { onDestroy } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminApplication,
    type AdminGrantCall,
    type ApplicationSummary,
    type CallBody,
    callApplications,
    deleteGrantCall,
    type GrantSubscriberList,
    grantSubscribers,
    listGrantCalls,
    listIdeas,
    patchGrantCall,
    removeGrantSubscriber,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import ApplicationSheet from "$lib/components/hub/application-sheet.svelte";
  import CallForm from "$lib/components/hub/call-form.svelte";
  import ContextMenu from "$lib/components/hub/context-menu.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import type { FolderTab, MenuItem } from "$lib/components/hub/types";
  import { dayWords, plural, registerNumber, when } from "$lib/format";
  import { applicationLabel, callState } from "$lib/grants";
  import { live } from "$lib/live/stream.svelte";
  import { showTip } from "$lib/tip";

  type View = "applications" | "call";
  type Filter = "all" | "review" | "accepted" | "rejected" | "draft";

  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: "Wszystkie" },
    { id: "review", label: "Do oceny" },
    { id: "accepted", label: "Przyjęte" },
    { id: "rejected", label: "Odrzucone" },
    { id: "draft", label: "Robocze" },
  ];
  const inFilter: Record<Filter, (a: ApplicationSummary) => boolean> = {
    accepted: (a) => a.status === "accepted",
    all: () => true,
    draft: (a) => a.status === "draft",
    rejected: (a) => a.status === "rejected",
    review: (a) => a.status === "submitted" || a.status === "in_review",
  };

  let calls = $state<AdminGrantCall[]>([]);
  let ideaCount = $state<{ total: number; fresh: number } | null>(null);
  let subscribers = $state<GrantSubscriberList | null>(null);
  let subscribersError = $state<Error | null>(null);
  let applications = $state<ApplicationSummary[]>([]);
  let appsFor = $state<string | null>(null);
  let loadError = $state<Error | null>(null);
  let appsError = $state<Error | null>(null);
  let loaded = $state(false);
  let wide = $state(true);
  let menu = $state<ContextMenu | null>(null);
  let busy = $state(false);

  const id = $derived(page.params.id ?? null);
  const creating = $derived(id === "new");
  const subscribersView = $derived(id === "subscribers");
  const params = $derived(page.url.searchParams);
  const view = $derived<View>(
    creating || params.get("view") === "call" ? "call" : "applications"
  );
  const filter = $derived<Filter>(
    filters.find((f) => f.id === params.get("status"))?.id ?? "all"
  );
  const openApp = $derived(params.get("app"));
  const call = $derived(calls.find((c) => c.id === id) ?? null);

  function href(
    target: string | null,
    next: { view?: View; status?: Filter; app?: string | null } = {}
  ) {
    const out = new URLSearchParams();
    const v = next.view ?? (target === id ? view : "applications");
    const f = next.status ?? (target === id ? filter : "all");
    const a = next.app === undefined ? null : next.app;
    if (v === "call" && target !== "new") {
      out.set("view", "call");
    }
    if (v === "applications" && f !== "all") {
      out.set("status", f);
    }
    if (v === "applications" && a) {
      out.set("app", a);
    }
    const path = target
      ? resolve("/grants/[[id]]", { id: target })
      : resolve("/grants/[[id]]", {});
    const text = out.toString();
    return `${path}${text ? `?${text}` : ""}`;
  }

  async function load() {
    try {
      calls = await listGrantCalls();
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e : new Error(String(e));
    } finally {
      loaded = true;
    }
  }

  async function loadApps(target: string) {
    try {
      const next = await callApplications(target);
      if (target === id) {
        applications = next;
        appsFor = target;
        appsError = null;
      }
    } catch (e) {
      appsError = e instanceof Error ? e : new Error(String(e));
    }
  }

  async function loadIdeas() {
    try {
      const found = await listIdeas();
      ideaCount = {
        fresh: found.items.filter((i) => i.status === "new").length,
        total: found.total,
      };
    } catch {
      ideaCount = null;
    }
  }

  async function loadSubscribers() {
    try {
      subscribers = await grantSubscribers();
      subscribersError = null;
    } catch (e) {
      subscribersError = e instanceof Error ? e : new Error(String(e));
    }
  }

  async function unsubscribe(subscriberId: string, anchor: HTMLElement) {
    try {
      await removeGrantSubscriber(subscriberId);
      await loadSubscribers();
      showTip(anchor, "Wypisano");
    } catch (e) {
      showTip(
        anchor,
        e instanceof ApiError ? e.message : "Nie udało się wypisać.",
        "bad"
      );
    }
  }

  const subscriberState = {
    confirmed: "potwierdzony",
    pending: "czeka na potwierdzenie",
    unsubscribed: "wypisany",
  } as const;

  $effect(() => {
    load();
    loadIdeas();
  });

  $effect(() => {
    if (subscribersView) {
      loadSubscribers();
    }
  });

  $effect(() => {
    if (id && !creating && !subscribersView) {
      loadApps(id);
    }
  });

  $effect(() => {
    if (loaded && !id && calls.length > 0) {
      goto(href(calls[0].id), { noScroll: true, replaceState: true });
    }
  });

  const shown = $derived(
    appsFor === id ? applications.filter(inFilter[filter]) : []
  );

  $effect(() => {
    if (
      wide &&
      view === "applications" &&
      !openApp &&
      shown.length > 0 &&
      appsFor === id
    ) {
      goto(href(id, { app: shown[0].id }), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
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

  const offs = [
    live.on("grant_call.updated", (data) => {
      const next = data as AdminGrantCall;
      const index = calls.findIndex((c) => c.id === next.id);
      calls =
        index === -1
          ? [next, ...calls]
          : calls.map((c) => (c.id === next.id ? next : c));
    }),
    live.on("application.submitted", (data) => {
      const next = data as ApplicationSummary;
      if (next.call_id === id && id) {
        loadApps(id);
      }
      load();
    }),
    live.on("application.updated", (data) => {
      const next = data as ApplicationSummary;
      if (next.call_id === id && id) {
        loadApps(id);
      }
    }),
  ];

  onDestroy(() => {
    for (const off of offs) {
      off();
    }
  });

  const ideaTabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: 0,
      href: resolve("/ideas/[[id]]", {}),
      id: "ideas",
      note:
        ideaCount && ideaCount.fresh > 0
          ? `${ideaCount.fresh} ${plural(ideaCount.fresh, "nowy", "nowe", "nowych")}`
          : undefined,
      size: ideaCount?.total ?? 0,
      title: "Pomysły mieszkańców",
      week: 0,
    },
  ]);

  const tabs = $derived<FolderTab[]>(
    calls.map((c) => ({
      cluster: null,
      fresh: 0,
      href: href(c.id),
      id: c.id,
      note:
        c.applications.submitted > 0
          ? `${c.applications.submitted} do oceny`
          : callState(c),
      size: c.applications.total,
      title: c.title,
      week: 0,
    }))
  );

  function range(c: AdminGrantCall) {
    return `od ${dayWords(c.opens_at)} do ${dayWords(c.closes_at)}`;
  }

  function saved(next: AdminGrantCall) {
    const index = calls.findIndex((c) => c.id === next.id);
    calls =
      index === -1
        ? [next, ...calls]
        : calls.map((c) => (c.id === next.id ? next : c));
    if (creating) {
      goto(href(next.id, { view: "call" }), { replaceState: true });
    }
  }

  async function act(
    target: AdminGrantCall,
    body: CallBody,
    done: string,
    anchor: HTMLElement | null
  ) {
    if (busy) {
      return;
    }
    busy = true;
    try {
      saved(await patchGrantCall(target.id, body));
      showTip(anchor, done);
    } catch (e) {
      showTip(
        anchor,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
    } finally {
      busy = false;
    }
  }

  async function remove(target: AdminGrantCall, anchor: HTMLElement | null) {
    try {
      await deleteGrantCall(target.id);
      calls = calls.filter((c) => c.id !== target.id);
      goto(href(calls[0]?.id ?? null), { replaceState: true });
    } catch (e) {
      showTip(
        anchor,
        e instanceof ApiError ? e.message : "Nie udało się usunąć.",
        "bad"
      );
    }
  }

  const nowIso = () => new Date().toISOString();

  function primaryAction(c: AdminGrantCall) {
    if (c.status === "draft") {
      return {
        body: { status: "published" } as CallBody,
        done: "Opublikowano",
        label: "Opublikuj nabór",
      };
    }
    if (c.status === "published" && c.phase === "upcoming") {
      return {
        body: { opens_at: nowIso() } as CallBody,
        done: "Nabór otwarty",
        label: "Otwórz teraz",
      };
    }
    if (c.status === "published" && c.phase === "open") {
      return {
        body: { closes_at: nowIso() } as CallBody,
        done: "Nabór zamknięty",
        label: "Zamknij nabór",
      };
    }
    return null;
  }

  function callMenu(c: AdminGrantCall, event: MouseEvent | KeyboardEvent) {
    const anchor = event.currentTarget as HTMLElement;
    const main = primaryAction(c);
    const items: (MenuItem | "-")[] = [
      {
        label: "Wnioski",
        run: () => goto(href(c.id, { view: "applications" })),
      },
      {
        label: "Ustawienia naboru",
        run: () => goto(href(c.id, { view: "call" })),
      },
      "-",
      ...(main
        ? [
            {
              label: main.label,
              run: () => act(c, main.body, main.done, anchor),
            },
          ]
        : []),
      ...(c.status === "published"
        ? [
            {
              label: "Cofnij do szkicu",
              run: () =>
                act(c, { status: "draft" }, "Cofnięto do szkicu", anchor),
            },
          ]
        : []),
      ...(c.status === "cancelled"
        ? []
        : [
            {
              label: "Anuluj nabór",
              run: () => act(c, { status: "cancelled" }, "Anulowano", anchor),
              tone: "bad" as const,
            },
          ]),
      ...(c.applications.total === 0
        ? [
            {
              label: "Usuń nabór",
              run: () => remove(c, anchor),
              tone: "bad" as const,
            },
          ]
        : []),
    ];
    menu?.show(event, items, anchor);
  }

  function changed(next: AdminApplication) {
    applications = applications.map((a) =>
      a.id === next.id ? { ...a, status: next.status } : a
    );
    load();
  }

  function keydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (
      view !== "applications" ||
      target.closest(
        "input, textarea, select, [contenteditable], [role='menu']"
      ) ||
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
    if (!(event.key in step) || shown.length === 0) {
      return;
    }
    event.preventDefault();
    const index = shown.findIndex((a) => a.id === openApp);
    const next =
      shown[Math.max(0, Math.min(shown.length - 1, index + step[event.key]))];
    goto(href(id, { app: next.id }), {
      keepFocus: true,
      noScroll: true,
      replaceState: true,
    });
  }

  const counts = $derived(
    Object.fromEntries(
      filters.map((f) => [
        f.id,
        appsFor === id ? applications.filter(inFilter[f.id]).length : 0,
      ])
    ) as Record<Filter, number>
  );
  const main = $derived(call ? primaryAction(call) : null);
</script>

<svelte:head>
  <title>Nabory · HubMi</title>
</svelte:head>

<svelte:window onkeydown={keydown} />

<div class={["binder", openApp && view === "applications" && "has-item"]}>
  <nav aria-label="Pomysły i nabory" class="rail">
    <p class="railh">Pomysły</p>
    <FolderTabs current="" tabs={ideaTabs} />
    <p class="railh">Nabory</p>
    <FolderTabs
      current={id ?? ""}
      oncontext={(tab, event) => {
        const c = calls.find((x) => x.id === tab.id);
        if (c) {
          callMenu(c, event);
        }
      }}
      {tabs}
    />
    <a
      aria-current={creating ? "true" : undefined}
      class="newtab"
      href={resolve("/grants/[[id]]", { id: "new" })}
    >
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
      Nowy nabór
    </a>
    <a
      aria-current={subscribersView ? "true" : undefined}
      class="newtab"
      href={resolve("/grants/[[id]]", { id: "subscribers" })}
    >
      Subskrybenci naborów
    </a>
  </nav>

  <main class={["board", calls[0]?.id === id && "first"]}>
    {#if loadError && !loaded}
      <ErrorState error={loadError} retry={load} />
    {:else if !loaded}
      <p class="text-hm-ink-soft text-sm">Wczytywanie…</p>
    {:else if creating}
      <header class="bhead">
        <h1
          class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
        >
          Nowy nabór
        </h1>
      </header>
      <div class="pane">
        <CallForm call={null} onsaved={saved} />
      </div>
    {:else if subscribersView}
      <header class="bhead">
        <div class="min-w-0">
          <h1
            class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
          >
            Subskrybenci naborów
          </h1>
          <p class="mt-1.5 max-w-[70ch] text-pretty text-hm-ink-soft text-sm">
            Osoby, które poprosiły o&nbsp;e-mail, gdy ruszy nowy nabór.
            Powiadomienie wychodzi samo przy publikacji i&nbsp;otwarciu naboru.
          </p>
        </div>
        {#if subscribers}
          <dl class="stats">
            <div>
              <dt>potwierdzonych</dt>
              <dd class="tabular">{subscribers.totals.confirmed}</dd>
            </div>
            <div>
              <dt>czeka na potwierdzenie</dt>
              <dd class="tabular">{subscribers.totals.pending}</dd>
            </div>
            <div>
              <dt>nieudanych wysyłek</dt>
              <dd class="tabular">{subscribers.totals.failed_deliveries}</dd>
            </div>
          </dl>
        {/if}
      </header>
      <div class="pane">
        {#if subscribersError && !subscribers}
          <ErrorState error={subscribersError} retry={loadSubscribers} />
        {:else if !subscribers}
          <p class="text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if subscribers.items.length === 0}
          <p class="text-hm-ink-soft text-sm">
            Nikt jeszcze nie zapisał się na powiadomienia o&nbsp;naborach.
          </p>
        {:else}
          <ol class="subs">
            {#each subscribers.items as sub (sub.id)}
              <li class={[sub.state === "unsubscribed" && "off"]}>
                <span class="grid min-w-0 gap-[3px]">
                  <span class="break-all font-semibold text-sm"
                    >{sub.email}</span
                  >
                  <span class="text-hm-ink-soft text-xs">
                    {subscriberState[sub.state]}
                    · zgoda {dayWords(sub.consent_at)}
                    · wysłano
                    {sub.sent}{sub.failed > 0 ? `, nie dotarło ${sub.failed}` : ""}
                  </span>
                </span>
                {#if sub.state !== "unsubscribed"}
                  <button
                    class="ghost cladd-clickable"
                    onclick={(event) => unsubscribe(sub.id, event.currentTarget)}
                    type="button"
                  >
                    <span>Wypisz</span>
                  </button>
                {/if}
              </li>
            {/each}
          </ol>
        {/if}
      </div>
    {:else if !call}
      <div class="grid content-start gap-3">
        <h1 class="font-semibold text-[26px] leading-tight tracking-tight">
          Nabory
        </h1>
        <p class="text-hm-ink-soft text-sm">
          {calls.length === 0 ? "Nie ma jeszcze żadnego naboru." : "Nie znaleziono tego naboru."}
        </p>
        <a
          class="primary cladd-clickable justify-self-start"
          href={resolve("/grants/[[id]]", { id: "new" })}
          ><span>Nowy nabór</span></a
        >
      </div>
    {:else}
      <header class="bhead">
        <div class="min-w-0">
          <h1
            class="text-balance font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
          >
            {call.title}
          </h1>
          <p class="mt-1.5 text-hm-ink-soft text-sm">
            <span
              class={["state", call.status === "published" && call.phase === "open" && "open"]}
              >{callState(call)}</span
            >
            · {range(call)}{call.demo ? " · Nabór pokazowy" : ""}
            {#if call.source_url}
              ·
              <a
                class="link"
                href={call.source_url}
                rel="noreferrer"
                target="_blank"
                >strona w&nbsp;ROPS</a
              >
            {/if}
          </p>
        </div>
        <div class="actions">
          <nav aria-label="Widok" class="filter">
            <a
              aria-current={view === "applications" ? "true" : undefined}
              data-sveltekit-noscroll
              data-sveltekit-replacestate
              href={href(call.id, { view: "applications" })}
            >
              Wnioski
              <span class="tabular count">{call.applications.total}</span>
            </a>
            <a
              aria-current={view === "call" ? "true" : undefined}
              data-sveltekit-noscroll
              data-sveltekit-replacestate
              href={href(call.id, { view: "call" })}
              >Ustawienia</a
            >
          </nav>
          {#if main}
            <button
              class="primary cladd-clickable"
              disabled={busy}
              onclick={(event) =>
                act(call, main.body, main.done, event.currentTarget)}
              type="button"
            >
              <span>{main.label}</span>
            </button>
          {/if}
        </div>
      </header>

      {#if view === "call"}
        <div class="pane">
          <CallForm {call} onsaved={saved} />
          <div class="more">
            <h2 class="font-semibold text-[13px]">Inne działania</h2>
            <div class="flex flex-wrap gap-2">
              {#if call.status === "published"}
                <button
                  class="ghost cladd-clickable"
                  onclick={(event) =>
                    act(call, { status: "draft" }, "Cofnięto do szkicu", event.currentTarget)}
                  type="button"
                >
                  <span>Cofnij do szkicu</span>
                </button>
              {/if}
              {#if call.status !== "cancelled"}
                <button
                  class="ghost bad cladd-clickable"
                  onclick={(event) =>
                    act(call, { status: "cancelled" }, "Anulowano", event.currentTarget)}
                  type="button"
                >
                  <span>Anuluj nabór</span>
                </button>
              {:else}
                <button
                  class="ghost cladd-clickable"
                  onclick={(event) =>
                    act(call, { status: "draft" }, "Przywrócono jako szkic", event.currentTarget)}
                  type="button"
                >
                  <span>Przywróć jako szkic</span>
                </button>
              {/if}
              {#if call.applications.total === 0}
                <button
                  class="ghost bad cladd-clickable"
                  onclick={(event) => remove(call, event.currentTarget)}
                  type="button"
                >
                  <span>Usuń nabór</span>
                </button>
              {/if}
            </div>
          </div>
        </div>
      {:else}
        <div class="work">
          <section aria-label="Wnioski" class="register">
            <div class="rhead">
              <nav aria-label="Stan wniosków" class="filter">
                {#each filters as f (f.id)}
                  <a
                    aria-current={filter === f.id ? "true" : undefined}
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href(call.id, { status: f.id })}
                  >
                    {f.label}
                    {#if f.id !== "all"}
                      <span class="tabular count">{counts[f.id]}</span>
                    {/if}
                  </a>
                {/each}
              </nav>
            </div>
            <div class="scroll">
              {#if appsError && appsFor !== id}
                <ErrorState
                  error={appsError}
                  retry={() => id && loadApps(id)}
                />
              {:else if appsFor !== id}
                <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
              {:else if shown.length === 0}
                <p class="px-3 py-6 text-hm-ink-soft text-sm">
                  {applications.length === 0 ? "W tym naborze nie ma jeszcze wniosków." : "Brak wniosków w tym stanie."}
                </p>
              {:else}
                <ol class="rows">
                  {#each shown as a (a.id)}
                    <li>
                      <a
                        aria-current={a.id === openApp ? "true" : undefined}
                        class={["row", a.status === "submitted" && "fresh"]}
                        data-sveltekit-noscroll
                        data-sveltekit-replacestate
                        href={href(call.id, { app: a.id })}
                      >
                        <span class="mono-num nr"
                          >{registerNumber(a.number)}</span
                        >
                        <span class="grid min-w-0 gap-[3px]">
                          <span class="t"
                            >{a.idea ? a.idea.title : "Wniosek bez pomysłu z Kreatora"}</span
                          >
                          <span class="text-hm-ink-soft text-xs">
                            {a.idea ? `Pomysł nr ${registerNumber(a.idea.number)} · ` : ""}
                            {a.submitted_at ? `złożony ${when(a.submitted_at)}` : `zmieniony ${when(a.updated_at)}`}{a.status === "draft" && a.missing_required.length > 0 ? ` · ${a.missing_required.length} ${plural(a.missing_required.length, "sekcja do uzupełnienia", "sekcje do uzupełnienia", "sekcji do uzupełnienia")}` : ""}
                          </span>
                        </span>
                        <span class={["st", `st-${a.status}`]}
                          >{applicationLabel[a.status]}</span
                        >
                      </a>
                    </li>
                  {/each}
                </ol>
              {/if}
            </div>
          </section>
          {#if openApp}
            <ApplicationSheet
              backHref={href(call.id, { app: null })}
              id={openApp}
              onchanged={changed}
            />
          {/if}
        </div>
      {/if}
    {/if}
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
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
    min-height: 0;
    overflow: auto;
    scrollbar-width: thin;
  }

  .rail :global(.tabs) {
    flex: none;
    height: auto;
    overflow: visible;
  }

  .railh {
    padding: 8px 0 2px 16px;
    margin: 0;
    font-size: 11px;
    font-weight: 700;
    color: var(--hm-ink-soft);
    text-transform: uppercase;
    letter-spacing: 0.1em;
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

  .subs {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .subs li {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    min-height: 56px;
    padding: 10px 4px;
    border-bottom: 1px solid var(--hm-rule);
  }

  .subs li.off {
    color: var(--hm-ink-soft);
  }

  .newtab {
    display: flex;
    gap: 8px;
    align-items: center;
    width: calc(100% - 12px);
    min-height: 52px;
    padding: 0 16px;
    margin-left: 12px;
    font-size: 14px;
    font-weight: 600;
    color: var(--hm-tab-ink-soft);
    border: 1.5px dashed
      color-mix(in oklab, var(--hm-tab-ink-soft) 45%, transparent);
    border-right: 0;
    border-radius: 16px 0 0 16px;
    transition:
      margin 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
      width 220ms cubic-bezier(0.2, 0.8, 0.2, 1),
      background-color 150ms ease,
      color 150ms ease;
  }

  .newtab:hover {
    width: calc(100% - 6px);
    margin-left: 6px;
    color: var(--hm-ink);
    background: var(--hm-tab-hover);
  }

  .newtab[aria-current="true"] {
    width: 100%;
    margin-left: 0;
    color: var(--hm-ink);
    background: var(--hm-board);
    border-color: transparent;
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
    gap: 12px 24px;
    align-items: end;
  }

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    justify-content: flex-end;
  }

  .state.open {
    font-weight: 600;
    color: var(--hm-ok);
  }

  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-decoration-color: color-mix(
      in oklab,
      var(--hm-stamp) 40%,
      transparent
    );
    text-underline-offset: 3px;
  }

  .pane {
    position: relative;
    display: grid;
    gap: 28px;
    align-content: start;
    min-height: 0;
    padding: 26px 30px 30px;
    overflow: auto;
    overscroll-behavior: contain;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: var(--hm-raised);
  }

  .more {
    display: grid;
    gap: 10px;
    max-width: 720px;
    padding-top: 18px;
    border-top: 1px solid var(--hm-rule);
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
    padding: 8px 0 10px;
    border-bottom: 1px solid var(--hm-rule);
  }

  .scroll {
    position: relative;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }

  .filter {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 2px;
    max-width: 100%;
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
    transition:
      background-color 150ms ease,
      color 150ms ease;
  }

  .filter a:hover {
    color: var(--hm-ink);
  }

  .filter a[aria-current="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.6),
      transparent
    );
    box-shadow: var(--shadow-cladd-outline);
  }

  .count {
    font-weight: 600;
  }

  .rows {
    padding: 0 0 8px;
    margin: 0;
    list-style: none;
  }

  .row {
    display: grid;
    grid-template-columns: 50px minmax(0, 1fr) auto;
    gap: 12px;
    align-items: baseline;
    min-height: 64px;
    padding: 12px;
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

  .nr {
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-ink-soft);
  }

  .fresh .nr {
    color: var(--hm-stamp);
  }

  .t {
    font-size: 14px;
    font-weight: 500;
  }

  .fresh .t {
    font-weight: 600;
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

  .st-submitted {
    font-weight: 650;
    color: var(--hm-stamp);
  }

  .st-in_review {
    color: var(--hm-ink);
  }

  .st-accepted {
    color: var(--hm-ok);
  }

  .primary {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    color: var(--hm-on-stamp);
    white-space: nowrap;
    background-color: var(--hm-stamp);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.16),
      transparent
    );
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-outline-fill);
    transition: background-color 150ms ease;
  }

  .primary:hover {
    background-color: var(--hm-stamp-press);
  }

  .primary:disabled {
    opacity: 0.6;
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

  .ghost.bad {
    color: var(--hm-bad);
  }

  @media (max-width: 899px) {
    .binder {
      grid-template-rows: auto 1fr;
      grid-template-columns: minmax(0, 1fr);
      padding: 0 10px 10px;
    }

    .rail {
      flex-direction: row;
      align-items: flex-end;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .rail :global(.tabs) {
      flex: none;
    }

    .railh {
      display: none;
    }

    .stats {
      flex-wrap: wrap;
      gap: 12px 20px;
    }

    .newtab,
    .newtab:hover {
      flex: none;
      width: auto;
      min-height: 92px;
      margin: 8px 0 0;
      border: 1.5px dashed
        color-mix(in oklab, var(--hm-tab-ink-soft) 45%, transparent);
      border-bottom: 0;
      border-radius: 16px 16px 0 0;
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

    .actions {
      justify-content: flex-start;
    }

    .pane {
      padding: 16px;
    }

    .scroll {
      overflow: visible;
    }

    .filter a,
    .primary,
    .ghost {
      height: 44px;
    }

    .row {
      grid-template-columns: 44px minmax(0, 1fr);
    }

    .row .st {
      grid-column: 2;
    }

    .has-item .register,
    .has-item .bhead,
    .has-item .rail {
      display: none;
    }

    .has-item .board {
      grid-template-rows: minmax(0, 1fr);
      padding: 0;
      background: none;
      box-shadow: none;
    }
  }
</style>
