<script lang="ts">
  import { onDestroy } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminIdea,
    type IdeaOptions,
    type IdeaStatus,
    ideaOptions,
    listIdeas,
  } from "$lib/api/admin";
  import ErrorState from "$lib/components/error-state.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import IdeaSheet from "$lib/components/hub/idea-sheet.svelte";
  import type { FolderTab } from "$lib/components/hub/types";
  import { clock, nbsp, registerNumber, when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";

  const labels: Record<IdeaStatus, string> = {
    accepted: "Przyjęty",
    in_review: "W ocenie",
    new: "Nowy",
    rejected: "Odrzucony",
  };
  const groups: { id: IdeaStatus; title: string }[] = [
    { id: "new", title: "Nowe" },
    { id: "in_review", title: "W ocenie" },
    { id: "accepted", title: "Przyjęte" },
    { id: "rejected", title: "Odrzucone" },
  ];

  let ideas = $state<AdminIdea[]>([]);
  let options = $state<IdeaOptions | null>(null);
  let loadError = $state<Error | null>(null);
  let loaded = $state(false);
  let arrived = $state(new Set<string>());
  let wide = $state(true);

  const id = $derived(page.params.id ?? null);
  const group = $derived(page.url.searchParams.get("status") ?? "all");
  const problem = $derived(page.url.searchParams.get("problem"));

  function href(target: string | null, next: { group?: string } = {}) {
    const g = next.group ?? group;
    const path = target
      ? resolve("/ideas/[[id]]", { id: target })
      : resolve("/ideas/[[id]]", {});
    const params = new URLSearchParams();
    if (g !== "all") {
      params.set("status", g);
    }
    if (problem) {
      params.set("problem", problem);
    }
    const q = params.toString();
    return q ? `${path}?${q}` : path;
  }

  async function load() {
    try {
      const [page1, opts] = await Promise.all([
        listIdeas(),
        ideaOptions().catch(() => null),
      ]);
      ideas = page1.items;
      options = opts;
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

  function upsert(idea: AdminIdea, fresh: boolean) {
    const index = ideas.findIndex((i) => i.id === idea.id);
    if (index === -1) {
      ideas = [idea, ...ideas];
      if (fresh) {
        arrived = new Set([...arrived, idea.id]);
      }
    } else {
      ideas[index] = { ...ideas[index], ...idea };
    }
  }

  const offs = [
    live.on("idea.created", (data) => upsert(data as AdminIdea, true)),
    live.on("idea.updated", (data) => upsert(data as AdminIdea, false)),
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

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: ideas.filter((i) => i.status === "new").length,
      href: href(null, { group: "all" }),
      id: "all",
      size: ideas.length,
      title: "Wszystkie pomysły",
      week: 0,
    },
    ...groups.map((g) => ({
      cluster: null,
      fresh: 0,
      href: href(null, { group: g.id }),
      id: g.id,
      size: ideas.filter((i) => i.status === g.id).length,
      title: g.title,
      week: 0,
    })),
  ]);

  const visible = $derived(
    ideas.filter(
      (i) =>
        (group === "all" || i.status === group) &&
        (!problem || i.problem_id === problem || i.problem?.id === problem)
    )
  );
  const problemTitle = $derived(
    problem
      ? (ideas.find((i) => i.problem?.id === problem)?.problem?.title ?? null)
      : null
  );
  const stageName = (slug: string) =>
    options?.stages.find((s) => s.slug === slug)?.name ?? slug;
  const today = new Date().toDateString();
  const stamp = (iso: string) =>
    new Date(iso).toDateString() === today ? clock(iso) : when(iso);

  $effect(() => {
    if (wide && !id && visible.length > 0) {
      goto(href(visible[0].id), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });
</script>

<svelte:head>
  <title>Pomysły · HubMi</title>
</svelte:head>

<div class={["binder", id && "has-item"]}>
  <nav aria-label="Stan pomysłów" class="rail">
    <FolderTabs current={group} {tabs} />
  </nav>

  <main class={["board", group === "all" && "first"]}>
    <header>
      <h1
        class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
      >
        {groups.find((g) => g.id === group)?.title ?? "Pomysły mieszkańców"}
      </h1>
      {#if problem}
        <p class="mt-1.5 text-sm">
          Odpowiadają na problem:
          <b class="font-semibold">{problemTitle ?? "wybrany problem"}</b>
          ·
          <a class="clear" href={resolve("/ideas/[[id]]", {})}
            >pokaż wszystkie</a
          >
        </p>
      {/if}
    </header>

    <div class="work">
      <section aria-label="Lista pomysłów" class="register">
        {#if loadError && ideas.length === 0}
          <ErrorState error={loadError} retry={load} />
        {:else if !loaded}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if visible.length === 0}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">
            {ideas.length === 0 ? "Nikt jeszcze nie zgłosił pomysłu. Pojawią się tutaj same." : "Brak pomysłów w tym stanie."}
          </p>
        {:else}
          <ol class="rows">
            {#each visible as idea (idea.id)}
              <li>
                <a
                  aria-current={idea.id === id ? "true" : undefined}
                  class={["row", `is-${idea.status}`, arrived.has(idea.id) && "hm-arrive"]}
                  data-sveltekit-noscroll
                  data-sveltekit-replacestate
                  href={href(idea.id)}
                >
                  <span class="nr mono-num">{registerNumber(idea.number)}</span>
                  <span class="grid min-w-0 gap-[3px]">
                    <span class="font-semibold text-sm"
                      >{nbsp(idea.title)}</span
                    >
                    <span class="lead">{nbsp(idea.essence)}</span>
                    <span class="text-hm-ink-soft text-xs"
                      >{stamp(idea.created_at)}
                      ·
                      {stageName(idea.stage)}{idea.problem ? ` · do: ${idea.problem.title}` : ""}</span
                    >
                  </span>
                  <span class="st">{labels[idea.status]}</span>
                </a>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      {#if id}
        <IdeaSheet
          backHref={href(null)}
          {id}
          onchange={(next) => upsert(next, false)}
          {options}
        />
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
    min-height: 0;
    border-top: 1px solid var(--hm-rule);
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
    grid-template-columns: 50px minmax(0, 1fr) 96px;
    gap: 12px;
    align-items: baseline;
    padding: 11px 12px 11px 4px;
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
    padding-left: 8px;
    font-size: 13px;
    color: var(--hm-ink-soft);
  }

  .is-new .nr {
    font-weight: 650;
    color: var(--hm-stamp);
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

  .is-accepted .st {
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

    .work {
      grid-template-columns: minmax(0, 1fr);
    }

    .row {
      grid-template-columns: 44px minmax(0, 1fr);
    }

    .st {
      grid-column: 2;
    }

    .has-item .register,
    .has-item header,
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
