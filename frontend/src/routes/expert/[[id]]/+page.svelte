<script lang="ts">
  import { untrack } from "svelte";
  import { goto } from "$app/navigation";
  import { resolve } from "$app/paths";
  import { page } from "$app/state";
  import {
    type Assignment,
    type ExpertAssignmentDetail,
    myAssignment,
    myAssignments,
    sendOpinion,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import FolderTabs from "$lib/components/hub/folder-tabs.svelte";
  import Stamp from "$lib/components/hub/stamp.svelte";
  import type { FolderTab } from "$lib/components/hub/types";
  import { nbsp, powiatName, when } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { showTip } from "$lib/tip";

  let list = $state<Assignment[]>([]);
  let loadError = $state<Error | null>(null);
  let loaded = $state(false);
  let detail = $state<ExpertAssignmentDetail | null>(null);
  let detailError = $state<Error | null>(null);
  let body = $state("");
  let note = $state("");
  let sending = $state(false);
  let sent = $state(false);
  let wide = $state(true);

  const id = $derived(page.params.id ?? null);
  const group = $derived(
    page.url.searchParams.get("stan") === "gotowe" ? "answered" : "open"
  );

  function href(target: string | null, g = group) {
    const path = target
      ? resolve("/expert/[[id]]", { id: target })
      : resolve("/expert/[[id]]", {});
    return g === "answered" ? `${path}?stan=gotowe` : path;
  }

  async function load() {
    try {
      list = await myAssignments();
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

  $effect(() => {
    const media = matchMedia("(min-width: 900px)");
    wide = media.matches;
    const update = () => {
      wide = media.matches;
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  });

  const visible = $derived(list.filter((a) => a.status === group));

  const tabs = $derived<FolderTab[]>([
    {
      cluster: null,
      fresh: list.filter((a) => a.status === "open").length,
      href: href(null, "open"),
      id: "open",
      size: list.filter((a) => a.status === "open").length,
      title: "Do zrobienia",
      week: 0,
    },
    {
      cluster: null,
      fresh: 0,
      href: href(null, "answered"),
      id: "answered",
      size: list.filter((a) => a.status === "answered").length,
      title: "Gotowe",
      week: 0,
    },
  ]);

  $effect(() => {
    if (wide && !id && visible.length > 0) {
      goto(href(visible[0].id), {
        keepFocus: true,
        noScroll: true,
        replaceState: true,
      });
    }
  });

  $effect(() => {
    const target = id;
    untrack(() => {
      detail = null;
      detailError = null;
      body = "";
      note = "";
      sent = false;
      if (target) {
        myAssignment(target)
          .then((d) => {
            if (target === id) {
              detail = d;
            }
          })
          .catch((e) => {
            detailError = e instanceof Error ? e : new Error(String(e));
          });
      }
    });
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    const button = document.getElementById("send-opinion");
    if (!detail || sending) {
      return;
    }
    if (!(body.trim() || note.trim())) {
      showTip(button, "Napisz opinię albo notatkę dla ROPS", "bad");
      return;
    }
    sending = true;
    try {
      const result = await sendOpinion(detail.id, body.trim(), note.trim());
      detail = {
        ...detail,
        ...result.assignment,
        messages: result.message
          ? [...detail.messages, result.message]
          : detail.messages,
        private_notes: result.private_note
          ? [...(detail.private_notes ?? []), result.private_note]
          : detail.private_notes,
      };
      list = list.map((a) =>
        a.id === result.assignment.id ? result.assignment : a
      );
      body = "";
      note = "";
      sent = true;
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Brak połączenia z serwerem.",
        "bad"
      );
    } finally {
      sending = false;
    }
  }

  const heading = (d: ExpertAssignmentDetail) => {
    if (d.kind === "need") {
      return d.item.number
        ? `Potrzeba nr ${String(d.item.number).padStart(4, "0")}`
        : "Potrzeba mieszkańca";
    }
    return d.item.title ?? "Pomysł mieszkańca";
  };

  const who = (m: ExpertAssignmentDetail["messages"][number]) => {
    if (m.direction === "from_author") {
      return "Autor";
    }
    if (m.expert) {
      return `Ekspert · ${m.expert.display_name}`;
    }
    return "ROPS";
  };
</script>

<svelte:head>
  <title>Moje zadania · HubMi</title>
</svelte:head>

<div class={["binder", id && "has-item"]}>
  <nav aria-label="Zadania" class="rail">
    <FolderTabs current={group} {tabs} />
  </nav>

  <main class={["board", group === "open" && "first"]}>
    <header class="bhead">
      <h1
        class="font-semibold text-[26px] leading-tight tracking-tight max-[899px]:text-[22px]"
      >
        {group === "open" ? "Prośby o opinię" : "Wydane opinie"}
      </h1>
    </header>

    <div class="work">
      <section aria-label="Lista zadań" class="register">
        {#if loadError && !loaded}
          <ErrorState error={loadError} retry={load} />
        {:else if !loaded}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">Wczytywanie…</p>
        {:else if visible.length === 0}
          <p class="px-3 py-6 text-hm-ink-soft text-sm">
            {group === "open" ? "Nie masz teraz żadnych próśb o opinię." : "Nie ma jeszcze wydanych opinii."}
          </p>
        {:else}
          <ol class="rows">
            {#each visible as a (a.id)}
              <li>
                <a
                  aria-current={a.id === id ? "true" : undefined}
                  class={["row", a.status === "open" && "unseen"]}
                  data-sveltekit-noscroll
                  data-sveltekit-replacestate
                  href={href(a.id)}
                >
                  <span class="grid min-w-0 gap-[3px]">
                    <span class="title2 font-semibold text-sm"
                      >{nbsp(a.title)}</span
                    >
                    {#if a.note}
                      <span class="lead">{a.note}</span>
                    {/if}
                    <span class="text-hm-ink-soft text-xs"
                      >{a.kind === "idea" ? "Pomysł" : "Potrzeba"}
                      · prośba od {a.assigned_by} · {when(a.created_at)}</span
                    >
                  </span>
                  <span class="st"
                    >{a.status === "open" ? "Czeka" : "Gotowe"}</span
                  >
                </a>
              </li>
            {/each}
          </ol>
        {/if}
      </section>

      {#if id}
        <article aria-labelledby="task-title" class="sheet">
          {#if detail}
            <form class="grid max-w-[680px] gap-[22px]" onsubmit={submit}>
              <a class="back" href={href(null)}>
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
                Zadania
              </a>
              <header
                class="flex items-start justify-between gap-4 max-[899px]:flex-col-reverse"
              >
                <div class="min-w-0">
                  <h2
                    class="font-semibold text-[22px] tracking-tight"
                    id="task-title"
                  >
                    {heading(detail)}
                  </h2>
                  <p class="mt-1.5 text-[13px] text-hm-ink-soft">
                    {detail.kind === "idea" ? "Pomysł mieszkańca" : "Potrzeba mieszkańca"}{detail.item.powiat ? ` · ${powiatName(detail.item.powiat, powiats.names)}` : ""}
                  </p>
                </div>
                {#key detail.id}
                  <Stamp
                    at={detail.item.created_at}
                    number={detail.item.number}
                  />
                {/key}
              </header>

              {#if detail.note}
                <p class="note">
                  <b class="font-semibold">Prośba ROPS:</b> {detail.note}
                </p>
              {/if}

              {#if detail.item.visualisation_url}
                <img
                  alt={detail.item.visualisation_alt ?? ""}
                  class="visual"
                  src={detail.item.visualisation_url}
                >
              {/if}

              <p class="reading">
                {nbsp(detail.item.essence ?? detail.item.text ?? "")}
              </p>
              {#if detail.item.for_whom}
                <p class="text-sm">
                  <b class="font-semibold">Dla kogo:</b> {detail.item.for_whom}
                </p>
              {/if}

              {#if detail.messages.length > 0}
                <section aria-labelledby="t-thread">
                  <h3 class="mb-1.5 font-semibold text-[13px]" id="t-thread">
                    Rozmowa z&nbsp;autorem
                  </h3>
                  <ol class="thread">
                    {#each detail.messages as m (m.id)}
                      <li>
                        <span class="text-hm-ink-soft text-xs"
                          ><b class="font-semibold text-hm-ink">{who(m)}</b>
                          · {when(m.sent_at)}</span
                        >
                        <p class="whitespace-pre-line text-sm">{m.body}</p>
                      </li>
                    {/each}
                  </ol>
                </section>
              {/if}

              {#if (detail.private_notes ?? []).length > 0}
                <section aria-labelledby="t-notes">
                  <h3 class="mb-1.5 font-semibold text-[13px]" id="t-notes">
                    Twoje notatki dla ROPS
                  </h3>
                  <ul class="thread">
                    {#each detail.private_notes ?? [] as n (n.id)}
                      <li>
                        <span class="text-hm-ink-soft text-xs"
                          >{when(n.created_at)}</span
                        >
                        <p class="text-sm">{n.body}</p>
                      </li>
                    {/each}
                  </ul>
                </section>
              {/if}

              <div class="grid gap-1.5">
                <label class="font-semibold text-[13px]" for="opinion"
                  >Opinia dla autora</label
                >
                <textarea
                  class="well"
                  id="opinion"
                  maxlength="5000"
                  placeholder="Autor zobaczy ją w swojej rozmowie z ROPS, podpisaną Twoim imieniem i dziedziną."
                  rows="5"
                  bind:value={body}
                ></textarea>
              </div>
              <div class="grid gap-1.5">
                <label class="font-semibold text-[13px]" for="private-note"
                  >Notatka tylko dla ROPS</label
                >
                <textarea
                  class="well"
                  id="private-note"
                  maxlength="2000"
                  rows="2"
                  bind:value={note}
                ></textarea>
              </div>
              <div class="foot">
                {#if sent}
                  <span class="sent hm-land stamp-word" role="status"
                    >Wysłano</span
                  >
                {/if}
                <button
                  class="primary cladd-clickable"
                  disabled={sending}
                  id="send-opinion"
                  type="submit"
                >
                  <span>{sending ? "Wysyłanie…" : "Wyślij opinię"}</span>
                </button>
              </div>
            </form>
          {:else if detailError}
            <ErrorState error={detailError} />
          {:else}
            <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
          {/if}
        </article>
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

  .title2 {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }

  .lead {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    font-size: 13px;
    color: var(--hm-ink-soft);
  }

  .st {
    display: inline-flex;
    gap: 6px;
    align-items: center;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ok);
    white-space: nowrap;
  }

  .st::before {
    width: 6px;
    height: 6px;
    content: "";
    background: currentColor;
    border-radius: 50%;
  }

  .unseen .st {
    color: var(--hm-stamp);
  }

  .sheet {
    position: relative;
    min-height: 0;
    padding: 26px 30px 0;
    overflow: auto;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: var(--hm-raised);
  }

  .back {
    display: none;
  }

  .note {
    padding: 12px 14px;
    font-size: 14px;
    background: var(--hm-stamp-wash);
    border-radius: 12px;
  }

  .visual {
    width: 100%;
    max-width: 420px;
    border-radius: 14px;
    box-shadow: 0 0 0 1px var(--hm-rule);
  }

  .reading {
    max-width: 62ch;
    font-size: 18px;
    line-height: 1.55;
    text-wrap: pretty;
    white-space: pre-line;
  }

  .thread {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .thread li {
    display: grid;
    gap: 3px;
    padding: 10px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .thread li:last-child {
    border-bottom: 0;
  }

  .well {
    width: 100%;
    border: 0;
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 14px;
    line-height: 1.5;
    background: var(--hm-sunk);
    box-shadow: var(--shadow-cladd-cut-outline);
    outline: none;
    resize: vertical;
    field-sizing: content;
  }

  .well::placeholder {
    color: var(--hm-ink-soft);
  }

  .well:focus {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .foot {
    position: sticky;
    bottom: 0;
    display: flex;
    gap: 14px;
    align-items: center;
    justify-content: flex-end;
    padding: 14px 0 20px;
    background: linear-gradient(to top, var(--hm-paper) 75%, transparent);
  }

  .sent {
    padding: 2px 8px;
    color: var(--hm-ok);
    border: 2px solid currentColor;
    border-radius: 6px;
    rotate: -4deg;
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
  }

  .primary:hover {
    background-color: var(--hm-stamp-press);
  }

  .primary:disabled {
    opacity: 0.6;
  }

  @media (max-width: 899px) {
    .binder {
      grid-template-rows: auto 1fr;
      grid-template-columns: minmax(0, 1fr);
      padding: 0 10px 10px;
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
      grid-template-columns: minmax(0, 1fr);
    }

    .sheet {
      padding: 16px 16px 0;
      border-radius: 18px;
    }

    .back {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      justify-self: start;
      min-height: 44px;
      font-size: 14px;
      font-weight: 500;
    }

    .reading {
      font-size: 16px;
    }

    .primary {
      height: 44px;
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
