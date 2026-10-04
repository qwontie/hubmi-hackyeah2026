<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type AdminFeedback,
    type AdminInnovation,
    type AdminTestSignup,
    type FeedbackByInnovation,
    feedbackByInnovation,
    listAllInnovations,
    listFeedback,
    listSignups,
    type SignupStatus,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import ContactSheet from "$lib/components/hub/contact-sheet.svelte";
  import ContextMenu from "$lib/components/hub/context-menu.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import OpinionSheet from "$lib/components/hub/opinion-sheet.svelte";
  import type { FolderTab, MenuItem } from "$lib/components/hub/types";
  import { plural, powiatName, when } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { live } from "$lib/live/stream.svelte";
  import {
    contactKey,
    fold,
    kindLabel,
    signupLabel,
    signupStatuses,
    whoLabel,
  } from "$lib/opinions";
  import { showTip } from "$lib/tip";

  type View = "votes" | "signups" | "comments";

  const WEEK = 7 * 86_400_000;
  const views: View[] = ["votes", "comments"];
  const viewTitle: Record<View, string> = {
    comments: "Uwagi i usprawnienia",
    signups: "Zgłoszenia do testów",
    votes: "Oceny innowacji",
  };
  const voteSorts = [
    { id: "recent", label: "Ostatnie" },
    { id: "fits", label: "Pasuje" },
    { id: "does_not_fit", label: "Nie pasuje" },
    { id: "testers", label: "Wolontariusze" },
  ];
  const signupSorts = [
    { id: "newest", label: "Najnowsze" },
    { id: "status", label: "Według stanu" },
  ];
  const kinds = [
    { id: "all", label: "Wszystkie" },
    { id: "improvement", label: "Usprawnienia" },
    { id: "does_not_fit", label: "Nie pasuje" },
    { id: "fits", label: "Pasuje" },
  ];
  const statusOrder: Record<SignupStatus, number> = {
    accepted: 1,
    closed: 4,
    new: 0,
    rejected: 3,
    reported: 2,
  };

  let rows = $state<FeedbackByInnovation[]>([]);
  let feedback = $state<AdminFeedback[]>([]);
  let signups = $state<AdminTestSignup[]>([]);
  let innovations = $state<Map<string, AdminInnovation>>(new Map());
  let loadError = $state<Error | null>(null);
  let loaded = $state(false);
  let wide = $state(true);
  let menu = $state<ContextMenu | null>(null);
  let query = $state("");
  let typing: ReturnType<typeof setTimeout> | undefined;

  const params = $derived(page.url.searchParams);
  const view = $derived<View>(
    views.find((v) => v === params.get("view")) ?? "votes"
  );
  const q = $derived(params.get("q") ?? "");
  const sort = $derived(
    params.get("sort") ?? (view === "signups" ? "newest" : "recent")
  );
  const status = $derived(
    signupStatuses.find((s) => s.id === params.get("status"))?.id ?? null
  );
  const kind = $derived(params.get("kind") ?? "all");
  const openSlug = $derived(params.get("innovation"));
  const openNote = $derived(params.get("note"));
  const openContact = $derived(params.get("contact"));
  let erasedContact = $state<{ id: string; email: string } | null>(null);
  const openEmail = $derived.by(() => {
    const found = signups.find((s) => s.id === openContact);
    if (found) {
      return contactKey(found.contact_email);
    }
    return erasedContact && erasedContact.id === openContact
      ? erasedContact.email
      : null;
  });

  function idOf(email: string): string | null {
    const key = contactKey(email);
    return signups.find((s) => contactKey(s.contact_email) === key)?.id ?? null;
  }
  const hasItem = $derived(Boolean(openSlug || openContact));

  $effect(() => {
    const next = q;
    untrack(() => {
      if (fold(next) !== fold(query)) {
        query = next;
      }
    });
  });

  interface State {
    contact: string | null;
    innovation: string | null;
    kind: string;
    note: string | null;
    q: string;
    sort: string;
    status: SignupStatus | null;
    view: View;
  }

  function href(next: Partial<State> = {}) {
    const s: State = {
      contact: openContact,
      innovation: openSlug,
      kind,
      note: "innovation" in next || "contact" in next ? null : openNote,
      q,
      sort,
      status,
      view,
      ...next,
    };
    const out = new URLSearchParams();
    if (s.view !== "votes") {
      out.set("view", s.view);
    }
    if (s.q.trim()) {
      out.set("q", s.q.trim());
    }
    const defaultSort = s.view === "signups" ? "newest" : "recent";
    if (s.view !== "comments" && s.sort && s.sort !== defaultSort) {
      out.set("sort", s.sort);
    }
    if (s.view === "signups" && s.status) {
      out.set("status", s.status);
    }
    if (s.view === "comments" && s.kind !== "all") {
      out.set("kind", s.kind);
    }
    if (s.contact) {
      out.set("contact", s.contact);
    } else if (s.innovation) {
      out.set("innovation", s.innovation);
      if (s.note) {
        out.set("note", s.note);
      }
    }
    const text = out.toString();
    return `${resolve("/opinions")}${text ? `?${text}` : ""}`;
  }

  const switchTo = (v: View) =>
    href({
      contact: null,
      innovation: null,
      kind: "all",
      sort: v === "signups" ? "newest" : "recent",
      status: null,
      view: v,
    });

  async function load() {
    try {
      const [a, b, c, d] = await Promise.all([
        feedbackByInnovation(),
        listFeedback(),
        listSignups(),
        listAllInnovations(),
      ]);
      rows = a;
      feedback = b;
      signups = c;
      innovations = new Map(d.map((i) => [i.slug, i]));
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
    live.on("feedback.created", () => load()),
    live.on("volunteer.created", () => load()),
    live.on("volunteer.updated", () => load()),
  ];

  onDestroy(() => {
    clearTimeout(typing);
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

  const categoryOf = (slug: string) =>
    innovations.get(slug)?.category.name ?? "";

  const recent = (iso: string | null) =>
    iso !== null && Date.now() - new Date(iso).getTime() < WEEK;

  const comments = $derived(feedback.filter((f) => f.comment));
  const needle = $derived(fold(q.trim()));
  const hit = (...parts: (string | null | undefined)[]) =>
    needle === "" || fold(parts.filter(Boolean).join(" ")).includes(needle);

  const votes = $derived.by(() => {
    const list = rows.filter((r) =>
      hit(r.innovation.title, categoryOf(r.innovation.slug))
    );
    const by: Record<string, (r: FeedbackByInnovation) => number> = {
      does_not_fit: (r) => r.does_not_fit,
      fits: (r) => r.fits,
      testers: (r) => r.testers,
    };
    const key = by[sort];
    if (!key) {
      return list;
    }
    return [...list].sort(
      (x, y) =>
        key(y) - key(x) ||
        x.innovation.title.localeCompare(y.innovation.title, "pl")
    );
  });

  const searchedSignups = $derived(
    signups.filter((s) =>
      hit(
        s.innovation.title,
        categoryOf(s.innovation.slug),
        s.contact_email,
        s.organization,
        s.note,
        whoLabel[s.who]
      )
    )
  );

  const statusCounts = $derived.by(() => {
    const counts: Record<SignupStatus, number> = {
      accepted: 0,
      closed: 0,
      new: 0,
      rejected: 0,
      reported: 0,
    };
    for (const s of searchedSignups) {
      counts[s.status] += 1;
    }
    return counts;
  });

  const shownSignups = $derived.by(() => {
    const list = searchedSignups.filter((s) => !status || s.status === status);
    if (sort !== "status") {
      return list;
    }
    return [...list].sort(
      (x, y) =>
        statusOrder[x.status] - statusOrder[y.status] ||
        y.created_at.localeCompare(x.created_at)
    );
  });

  const shownComments = $derived(
    comments.filter(
      (c) =>
        (kind === "all" || c.kind === kind) &&
        hit(c.comment, c.innovation.title, categoryOf(c.innovation.slug))
    )
  );

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: 0,
      href: switchTo("votes"),
      id: "votes",
      size: rows.length,
      title: viewTitle.votes,
      week: rows.filter((r) => recent(r.last_at)).length,
    },
    {
      cluster: null,
      fresh: 0,
      href: switchTo("comments"),
      id: "comments",
      size: comments.length,
      title: viewTitle.comments,
      week: comments.filter((c) => recent(c.updated_at)).length,
    },
  ]);

  const keys = $derived.by(() => {
    if (view === "signups") {
      const seen: string[] = [];
      for (const s of shownSignups) {
        const k = contactKey(s.contact_email);
        if (!seen.includes(k)) {
          seen.push(k);
        }
      }
      return seen.map((k) => ({
        contact: idOf(k),
        innovation: null,
        note: null,
      }));
    }
    if (view === "comments") {
      return shownComments.map((c) => ({
        contact: null,
        innovation: c.innovation.slug,
        note: c.id,
      }));
    }
    return votes.map((r) => ({
      contact: null,
      innovation: r.innovation.slug,
      note: null,
    }));
  });

  $effect(() => {
    if (wide && loaded && !hasItem && keys.length > 0) {
      goto(href(keys[0]), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  function search(value: string) {
    query = value;
    clearTimeout(typing);
    typing = setTimeout(() => {
      goto(href({ contact: null, innovation: null, q: value }), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }, 220);
  }

  function copy(text: string, anchor: HTMLElement | null, done: string) {
    navigator.clipboard
      .writeText(text)
      .then(() => showTip(anchor, done))
      .catch(() => showTip(anchor, "Nie udało się skopiować.", "bad"));
  }

  const open = (target: Partial<State>) =>
    goto(href(target), { noScroll: true, replaceState: true });

  function innovationMenu(
    slug: string,
    event: MouseEvent | KeyboardEvent,
    anchor: HTMLElement
  ) {
    menu?.show(
      event,
      [
        {
          hint: "Enter",
          label: "Otwórz opinie",
          run: () => open({ contact: null, innovation: slug }),
        },
        {
          label: "Otwórz w Bibliotece",
          run: () => goto(resolve("/library/[[slug]]", { slug })),
        },
        "-",
        {
          label: "Kopiuj link",
          run: () =>
            copy(
              `${location.origin}${href({ contact: null, innovation: slug })}`,
              anchor,
              "Skopiowano link"
            ),
        },
      ],
      anchor
    );
  }

  function signupMenu(
    signup: AdminTestSignup,
    event: MouseEvent | KeyboardEvent,
    anchor: HTMLElement
  ) {
    const items: (MenuItem | "-")[] = [
      {
        hint: "Enter",
        label: "Otwórz kontakt",
        run: () =>
          open({ contact: idOf(signup.contact_email), innovation: null }),
      },
      {
        label: "Opinie o tej innowacji",
        run: () =>
          goto(
            href({
              contact: null,
              innovation: signup.innovation.slug,
              view: "votes",
            })
          ),
      },
      {
        label: "Otwórz zgłoszenie wolontariusza",
        run: () => goto(resolve("/volunteers/[[id]]", { id: signup.id })),
      },
      "-",
      {
        label: "Otwórz w programie pocztowym",
        run: () => {
          location.href = `mailto:${signup.contact_email}`;
        },
      },
      {
        label: "Kopiuj adres e-mail",
        run: () => copy(signup.contact_email, anchor, "Skopiowano adres"),
      },
    ];
    menu?.show(event, items, anchor);
  }

  function rowKeys(event: KeyboardEvent, run: (anchor: HTMLElement) => void) {
    if (
      event.key === "ContextMenu" ||
      (event.shiftKey && event.key === "F10")
    ) {
      run(event.currentTarget as HTMLElement);
    }
  }

  function move(step: number) {
    if (keys.length === 0) {
      return;
    }
    const index = keys.findIndex((k) => {
      if (k.contact) {
        return k.contact === openContact;
      }
      if (k.note) {
        return k.note === openNote;
      }
      return k.innovation === openSlug && !openContact;
    });
    const next =
      keys[Math.max(0, Math.min(keys.length - 1, index + step))] ?? keys[0];
    goto(href(next), { keepFocus: true, noScroll: true, replaceState: true });
    requestAnimationFrame(() => {
      document
        .querySelector('.rows [aria-current="true"]')
        ?.scrollIntoView({ block: "nearest" });
    });
  }

  function keydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement;
    if (
      target.closest("input, textarea, select, [contenteditable]") ||
      target.closest('[role="menu"]') ||
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
    } else if (event.key === "/") {
      event.preventDefault();
      document.getElementById("opinions-search")?.focus();
    }
  }

  const sameContact = (s: AdminTestSignup) =>
    openEmail !== null && contactKey(s.contact_email) === openEmail;

  const placeholder = $derived(
    {
      comments: "Szukaj w uwagach, innowacjach i kategoriach",
      signups: "Szukaj innowacji, kategorii lub kontaktu",
      votes: "Szukaj innowacji lub kategorii",
    }[view]
  );

  const counted = $derived(
    {
      comments: `${shownComments.length} ${plural(shownComments.length, "uwaga", "uwagi", "uwag")}`,
      signups: `${shownSignups.length} ${plural(shownSignups.length, "zgłoszenie", "zgłoszenia", "zgłoszeń")}`,
      votes: `${votes.length} ${plural(votes.length, "innowacja", "innowacje", "innowacji")}`,
    }[view]
  );

  const backHref = $derived(href({ contact: null, innovation: null }));
</script>

<svelte:head>
  <title>Opinie i zgłoszenia · HubMi</title>
</svelte:head>

<svelte:window onkeydown={keydown} />

<div class={["binder", hasItem && "has-item"]}>
  <nav aria-label="Rodzaje opinii" class="rail">
    <FolderTabs current={view} {tabs} />
  </nav>

  <main class={["board", view === "votes" && "first"]}>
    <header class="bhead">
      <h1
        class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
      >
        {viewTitle[view]}
      </h1>
    </header>

    <div class="work">
      <section aria-label={viewTitle[view]} class="register">
        <div class="rhead">
          <label class="search">
            <span class="sr-only">{placeholder}</span>
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
              id="opinions-search"
              oninput={(event) => search(event.currentTarget.value)}
              {placeholder}
              type="search"
              value={query}
            >
            <kbd aria-hidden="true" class="max-[899px]:hidden">/</kbd>
          </label>
          <div class="controls">
            {#if view === "votes"}
              <nav aria-label="Kolejność" class="filter">
                {#each voteSorts as s (s.id)}
                  <a
                    aria-current={s.id === sort ? "true" : undefined}
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href({ contact: null, innovation: null, sort: s.id })}
                    >{s.label}</a
                  >
                {/each}
              </nav>
            {:else if view === "signups"}
              <nav aria-label="Stan zgłoszenia" class="filter">
                <a
                  aria-current={status === null ? "true" : undefined}
                  data-sveltekit-noscroll
                  data-sveltekit-replacestate
                  href={href({ contact: null, innovation: null, status: null })}
                  >Wszystkie</a
                >
                {#each signupStatuses as st (st.id)}
                  <a
                    aria-current={status === st.id ? "true" : undefined}
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href({ contact: null, innovation: null, status: st.id })}
                  >
                    {st.label}
                    <span class="count tabular">{statusCounts[st.id]}</span>
                  </a>
                {/each}
              </nav>
              <nav aria-label="Kolejność" class="filter">
                {#each signupSorts as s (s.id)}
                  <a
                    aria-current={s.id === sort ? "true" : undefined}
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href({ contact: null, innovation: null, sort: s.id })}
                    >{s.label}</a
                  >
                {/each}
              </nav>
            {:else}
              <nav aria-label="Rodzaj" class="filter">
                {#each kinds as k (k.id)}
                  <a
                    aria-current={k.id === kind ? "true" : undefined}
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href({ contact: null, innovation: null, kind: k.id })}
                    >{k.label}</a
                  >
                {/each}
              </nav>
            {/if}
            <span aria-live="polite" class="total tabular">{counted}</span>
          </div>
        </div>

        <div class="scroll">
          {#if loadError && !loaded}
            <ErrorState error={loadError} retry={load} />
          {:else if !loaded}
            <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
          {:else if view === "votes"}
            {#if votes.length === 0}
              <p class="px-3 py-6 text-hm-ink-soft text-sm">
                {rows.length === 0 ? "Nikt jeszcze nie ocenił żadnej innowacji." : "Nic nie pasuje do wyszukiwania."}
              </p>
            {:else}
              <div aria-hidden="true" class="colhead">
                <span>Innowacja</span>
                <span class={[sort === "fits" && "on"]}>Pasuje</span>
                <span class={[sort === "does_not_fit" && "on"]}
                  >Nie pasuje</span
                >
                <span class="opt">Uwagi</span>
                <span class={[sort === "testers" && "on"]}>Wolontariusze</span>
              </div>
              <ol class="rows">
                {#each votes as r (r.innovation.slug)}
                  <li>
                    <a
                      aria-current={r.innovation.slug === openSlug && !openContact
                      ? "true"
                      : undefined}
                      class="row vrow"
                      data-sveltekit-noscroll
                      data-sveltekit-replacestate
                      href={href({ contact: null, innovation: r.innovation.slug })}
                      oncontextmenu={(event) =>
                      innovationMenu(r.innovation.slug, event, event.currentTarget)}
                      onkeydown={(event) =>
                      rowKeys(event, (a) =>
                        innovationMenu(r.innovation.slug, event, a)
                      )}
                    >
                      <span class="grid min-w-0 gap-[3px]">
                        <span class="font-semibold text-sm"
                          >{r.innovation.title}</span
                        >
                        <span class="text-hm-ink-soft text-xs"
                          >{categoryOf(r.innovation.slug)}{r.last_at ? ` · ${when(r.last_at)}` : ""}</span
                        >
                      </span>
                      <span class="num tabular"
                        ><span class="sr-only">Pasuje: </span>{r.fits}</span
                      >
                      <span
                        class={["num tabular", r.does_not_fit > r.fits && "worse"]}
                        ><span class="sr-only">Nie pasuje: </span>
                        {r.does_not_fit}</span
                      >
                      <span class="num opt tabular"
                        ><span class="sr-only">Uwagi: </span>
                        {r.improvements}</span
                      >
                      <span class="num tabular"
                        ><span class="sr-only">Wolontariusze: </span>
                        {r.testers}</span
                      >
                    </a>
                  </li>
                {/each}
              </ol>
            {/if}
          {:else if view === "signups"}
            {#if shownSignups.length === 0}
              <p class="px-3 py-6 text-hm-ink-soft text-sm">
                {signups.length === 0 ? "Nikt jeszcze nie zgłosił się do testów." : "Nic nie pasuje do wyszukiwania."}
              </p>
            {:else}
              <ol class="rows">
                {#each shownSignups as s (s.id)}
                  <li>
                    <a
                      aria-current={sameContact(s) ? "true" : undefined}
                      class="row srow"
                      data-sveltekit-noscroll
                      data-sveltekit-replacestate
                      href={href({ contact: idOf(s.contact_email), innovation: null })}
                      oncontextmenu={(event) =>
                      signupMenu(s, event, event.currentTarget)}
                      onkeydown={(event) =>
                      rowKeys(event, (a) => signupMenu(s, event, a))}
                    >
                      <span class="grid min-w-0 gap-[3px]">
                        <span class="font-semibold text-sm"
                          >{s.organization || s.contact_email}</span
                        >
                        <span class="text-sm">{s.innovation.title}</span>
                        <span class="text-hm-ink-soft text-xs">
                          {whoLabel[s.who]}{s.powiat ? ` · ${powiatName(s.powiat, powiats.names)}` : ""}
                          · {when(s.created_at)}
                        </span>
                      </span>
                      <span class={["st", `st-${s.status}`]}
                        >{signupLabel[s.status]}</span
                      >
                    </a>
                  </li>
                {/each}
              </ol>
            {/if}
          {:else if shownComments.length === 0}
            <p class="px-3 py-6 text-hm-ink-soft text-sm">
              {comments.length === 0 ? "Nikt jeszcze nie zostawił uwag." : "Nic nie pasuje do wyszukiwania."}
            </p>
          {:else}
            <ol class="rows">
              {#each shownComments as c (c.id)}
                <li>
                  <a
                    aria-current={c.id === openNote ? "true" : undefined}
                    class="row crow"
                    data-sveltekit-noscroll
                    data-sveltekit-replacestate
                    href={href({ contact: null, innovation: c.innovation.slug, note: c.id })}
                    oncontextmenu={(event) =>
                    innovationMenu(c.innovation.slug, event, event.currentTarget)}
                    onkeydown={(event) =>
                    rowKeys(event, (a) =>
                      innovationMenu(c.innovation.slug, event, a)
                    )}
                  >
                    <span class="text-hm-ink-soft text-xs">
                      <b class="font-semibold text-hm-ink"
                        >{kindLabel[c.kind]}</b
                      >
                      · {c.innovation.title} · {when(c.updated_at)}
                    </span>
                    <span class="quote">{c.comment}</span>
                  </a>
                </li>
              {/each}
            </ol>
          {/if}
        </div>
      </section>

      {#if openEmail}
        <ContactSheet
          {backHref}
          email={openEmail}
          innovationHref={(slug) =>
            href({ contact: null, innovation: slug, view: "votes" })}
          onerased={() => {
            if (openContact && openEmail) {
              erasedContact = { email: openEmail, id: openContact };
            }
            load();
          }}
          signups={signups.filter(sameContact)}
        />
      {:else if openSlug}
        <OpinionSheet
          {backHref}
          category={categoryOf(openSlug)}
          comments={comments.filter((c) => c.innovation.slug === openSlug)}
          contactHref={(email) =>
            href({ contact: idOf(email), innovation: null, view: "signups" })}
          highlight={openNote}
          row={rows.find((r) => r.innovation.slug === openSlug) ?? null}
          signups={signups.filter((s) => s.innovation.slug === openSlug)}
          slug={openSlug}
          title={innovations.get(openSlug)?.title ?? ""}
        />
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

  .scroll {
    position: relative;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
  }

  .rhead {
    display: grid;
    gap: 8px;
    padding: 8px 0 10px;
    border-bottom: 1px solid var(--hm-rule);
  }

  .search {
    display: flex;
    gap: 8px;
    align-items: center;
    height: 36px;
    padding: 0 8px 0 10px;
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

  kbd {
    display: grid;
    place-items: center;
    min-width: 20px;
    height: 20px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--hm-ink-soft);
    background: var(--hm-board);
    border-radius: 5px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  .total {
    margin-left: auto;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
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
    color: var(--hm-ink-soft);
  }

  .colhead {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 56px 76px 52px 92px;
    gap: 4px;
  }

  .colhead {
    position: sticky;
    top: 0;
    z-index: 1;
    align-items: end;
    padding: 10px 12px 6px;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.2;
    color: var(--hm-ink-soft);
    background: var(--hm-board);
    border-bottom: 1px solid var(--hm-rule);
  }

  .colhead span:not(:first-child) {
    text-align: right;
  }

  .colhead .on {
    font-weight: 650;
    color: var(--hm-ink);
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 4px;
  }

  .rows {
    padding: 0 0 8px;
    margin: 0;
    list-style: none;
  }

  .row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: baseline;
    min-height: 58px;
    padding: 11px 12px;
    border-bottom: 1px solid var(--hm-rule);
    transition: background-color 150ms ease;
  }

  .vrow {
    grid-template-columns: minmax(0, 1fr) 56px 76px 52px 92px;
    gap: 4px;
  }

  .crow {
    grid-template-columns: minmax(0, 1fr);
    gap: 4px;
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

  .num {
    font-size: 14px;
    font-weight: 560;
    text-align: right;
  }

  .num.worse {
    font-weight: 650;
    color: var(--hm-bad);
  }

  .quote {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 14px;
    line-height: 1.45;
    text-wrap: pretty;
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

  .st-new {
    font-weight: 650;
    color: var(--hm-stamp);
  }

  .st-contacted {
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

    .search,
    .filter a {
      height: 44px;
    }

    .filter {
      max-width: 100%;
      overflow-x: auto;
      scrollbar-width: none;
    }

    .total {
      margin-left: 0;
    }

    .colhead,
    .vrow {
      grid-template-columns: minmax(0, 1fr) 44px 68px 88px;
    }

    .opt,
    kbd {
      display: none;
    }

    .colhead {
      padding: 10px 8px 6px;
      font-size: 11px;
    }

    .row {
      padding: 11px 8px;
    }

    .scroll {
      overflow: visible;
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
