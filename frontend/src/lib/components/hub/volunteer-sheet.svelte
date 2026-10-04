<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { resolve } from "$app/paths";
  import {
    type AdminVolunteer,
    type AdminVolunteerDetail,
    acceptVolunteer,
    closeVolunteer,
    getVolunteer,
    rejectVolunteer,
    type VolunteerMessage,
    writeToVolunteer,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import { dayWords, nbsp, when } from "$lib/format";
  import { live } from "$lib/live/stream.svelte";
  import { whoLabel } from "$lib/opinions";
  import { showTip } from "$lib/tip";
  import {
    deliveryWord,
    messageKind,
    recommendLabel,
    volunteerLabel,
  } from "$lib/volunteers";

  let {
    id,
    backHref,
    onchange,
  }: {
    id: string;
    backHref: string;
    onchange: (volunteer: AdminVolunteer) => void;
  } = $props();

  type Decision = "accept" | "reject" | null;

  let detail = $state<AdminVolunteerDetail | null>(null);
  let loadError = $state<Error | null>(null);
  let decision = $state<Decision>(null);
  let letter = $state("");
  let reason = $state("");
  let body = $state("");
  let busy = $state(false);
  let stamp = $state<"sent" | "saved" | "failed" | null>(null);
  let controller: AbortController | null = null;

  async function load(target: string) {
    controller?.abort();
    controller = new AbortController();
    loadError = null;
    try {
      const next = await getVolunteer(target, controller.signal);
      if (target === id) {
        detail = next;
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return;
      }
      loadError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    const target = id;
    untrack(() => {
      detail = null;
      decision = null;
      letter = "";
      reason = "";
      body = "";
      stamp = null;
      load(target);
    });
  });

  const offs = [
    live.on("volunteer.updated", (data) => {
      if ((data as AdminVolunteer).id === id) {
        load(id);
      }
    }),
    live.on("volunteer.reported", (data) => {
      if ((data as AdminVolunteer).id === id) {
        load(id);
      }
    }),
  ];

  onDestroy(() => {
    controller?.abort();
    for (const off of offs) {
      off();
    }
  });

  function startDecision(kind: Exclude<Decision, null>) {
    if (!detail) {
      return;
    }
    decision = kind;
    reason = "";
    letter = kind === "accept" ? detail.drafts.accept : detail.drafts.reject;
  }

  const letterPreview = $derived(
    decision === "reject"
      ? letter.replaceAll("{reason}", reason.trim() || "{reason}")
      : letter
  );

  function applied(next: AdminVolunteerDetail) {
    detail = next;
    decision = null;
    onchange(next);
  }

  function failed(anchor: HTMLElement | null, e: unknown, fallback: string) {
    showTip(anchor, e instanceof ApiError ? e.message : fallback, "bad");
  }

  async function decide(event: SubmitEvent) {
    event.preventDefault();
    if (!detail || busy || !decision) {
      return;
    }
    const form = event.currentTarget as HTMLFormElement;
    const anchor = form.querySelector<HTMLElement>("button[type=submit]");
    if (decision === "reject" && reason.trim().length < 3) {
      showTip(anchor, "Podaj powód odmowy.", "bad");
      return;
    }
    busy = true;
    try {
      const text = letterPreview.trim();
      const next =
        decision === "accept"
          ? await acceptVolunteer(detail.id, text || null)
          : await rejectVolunteer(detail.id, reason.trim(), text || null);
      applied(next);
      showTip(anchor, decision === "accept" ? "Przyjęto" : "Odrzucono");
    } catch (e) {
      failed(anchor, e, "Nie udało się zapisać.");
    } finally {
      busy = false;
    }
  }

  async function close(event: MouseEvent) {
    if (!detail || busy) {
      return;
    }
    const anchor = event.currentTarget as HTMLElement;
    busy = true;
    try {
      applied(await closeVolunteer(detail.id));
      showTip(anchor, "Zamknięto");
    } catch (e) {
      failed(anchor, e, "Nie udało się zamknąć.");
    } finally {
      busy = false;
    }
  }

  async function send(event: SubmitEvent) {
    event.preventDefault();
    if (!detail || busy) {
      return;
    }
    const form = event.currentTarget as HTMLFormElement;
    const anchor = form.querySelector<HTMLElement>("button[type=submit]");
    const text = body.trim();
    if (text.length < 2) {
      showTip(anchor, "Najpierw napisz wiadomość.", "bad");
      return;
    }
    busy = true;
    stamp = null;
    try {
      const message = await writeToVolunteer(detail.id, text);
      detail.messages = [...detail.messages, message];
      body = "";
      stamp = stampFor(message);
    } catch (e) {
      failed(anchor, e, "Brak połączenia z serwerem.");
    } finally {
      busy = false;
    }
  }

  function stampFor(m: VolunteerMessage): "sent" | "saved" | "failed" {
    if (m.delivery_status === "failed") {
      return "failed";
    }
    if (m.delivery_status === "skipped") {
      return "saved";
    }
    return "sent";
  }

  const stampWords = {
    failed: "Nie wysłano",
    saved: "Zapisano",
    sent: "Wysłano",
  };

  function keydown(event: KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      (event.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
    }
  }

  const reportFields = [
    { key: "activity", label: "Co zrobiłem i z kim" },
    { key: "worked", label: "Co zadziałało" },
    { key: "not_worked", label: "Co nie zadziałało, co bym zmienił" },
  ] as const;
</script>

<article aria-labelledby="volunteer-title" class="sheet">
  {#if detail}
    <div class="grid max-w-[680px] gap-[22px]">
      <a class="back" href={backHref}>
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
        Wolontariusze
      </a>
      <header class="grid gap-1.5">
        <p class="text-[13px] text-hm-ink-soft">
          Zgłoszenie z&nbsp;{dayWords(detail.created_at)}
          ·
          <span class={["state", `st-${detail.status}`]}
            >{volunteerLabel[detail.status]}</span
          >
        </p>
        <h2
          class="break-words font-semibold text-[22px] tracking-tight"
          id="volunteer-title"
        >
          {detail.organization || detail.email}
        </h2>
        <p class="text-[13px] text-hm-ink-soft">
          {[whoLabel[detail.who], detail.powiat_name, detail.organization ? detail.email : ""]
            .filter(Boolean)
            .join(" · ")}
        </p>
        <a
          class="link inline-flex min-h-10 w-fit items-center text-[13px] md:min-h-0"
          href="{resolve('/opinions')}?contact={detail.id}"
          >Wszystko z&nbsp;tego adresu, usunięcie danych</a
        >
      </header>

      <dl class="who">
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
          <dt>Powiat</dt>
          <dd>{detail.powiat_name || "nie podano"}</dd>
        </div>
      </dl>

      <section aria-labelledby="prop-h">
        <h3 class="h3" id="prop-h">Co chce zrobić</h3>
        {#if detail.proposal.trim()}
          <p class="quote">{nbsp(detail.proposal)}</p>
        {:else}
          <p class="text-[13px] text-hm-ink-soft">
            Osoba nie napisała, co chce zrobić.
          </p>
        {/if}
      </section>

      {#if detail.status === "new"}
        <section aria-labelledby="dec-h" class="grid gap-2">
          <h3 class="h3" id="dec-h">Decyzja</h3>
          {#if decision === null}
            <div class="flex flex-wrap gap-2">
              <button
                class="primary cladd-clickable"
                onclick={() => startDecision("accept")}
                type="button"
              >
                <span>Przyjmij</span>
              </button>
              <button
                class="ghost cladd-clickable"
                onclick={() => startDecision("reject")}
                type="button"
              >
                <span>Odrzuć</span>
              </button>
            </div>
            <p class="text-[13px] text-hm-ink-soft">
              Każda decyzja idzie e-mailem do tej osoby. List możesz poprawić
              przed wysłaniem.
            </p>
          {:else}
            <form class="grid gap-2" onsubmit={decide}>
              {#if decision === "reject"}
                <label class="grid gap-1 text-[13px]" for="reject-reason">
                  <span class="font-semibold">Powód odmowy</span>
                  <input
                    class="field"
                    id="reject-reason"
                    maxlength="2000"
                    required
                    bind:value={reason}
                  >
                </label>
              {/if}
              <label class="grid gap-1 text-[13px]" for="decision-letter">
                <span class="font-semibold">
                  {decision === "accept" ? "List z przyjęciem" : "List z odmową"}
                </span>
                <span class="text-hm-ink-soft">
                  {decision === "accept"
                    ? "Pod treścią serwer doda osobisty link do raportu."
                    : "Napis {reason} zostanie zastąpiony powodem."}
                </span>
              </label>
              <div class="reply">
                <textarea
                  id="decision-letter"
                  maxlength="5000"
                  rows="6"
                  bind:value={letter}
                ></textarea>
                <div class="flex items-center justify-end gap-2 p-1.5">
                  <button
                    class="ghost"
                    onclick={() => {
                      decision = null;
                    }}
                    type="button"
                  >
                    <span>Anuluj</span>
                  </button>
                  <button
                    class="primary cladd-clickable"
                    disabled={busy}
                    type="submit"
                  >
                    <span>
                      {decision === "accept" ? "Przyjmij i wyślij" : "Odrzuć i wyślij"}
                    </span>
                  </button>
                </div>
              </div>
            </form>
          {/if}
        </section>
      {:else if detail.status === "rejected"}
        <p class="text-[13px] text-hm-ink-soft">
          Odrzucone{detail.decided_at ? ` ${when(detail.decided_at)}` : ""}{detail.decision_reason ? `: ${detail.decision_reason}` : ""}.
        </p>
      {:else if detail.status === "closed"}
        <p class="text-[13px] text-hm-ink-soft">
          Zamknięte{detail.decided_at ? ` ${when(detail.decided_at)}` : ""}.
          Raport jest tylko do odczytu.
        </p>
      {:else}
        <div class="flex flex-wrap items-center gap-3">
          <button
            class="ghost cladd-clickable"
            disabled={busy}
            onclick={close}
            type="button"
          >
            <span>Zamknij zgłoszenie</span>
          </button>
          <span class="text-[13px] text-hm-ink-soft">
            {detail.status === "accepted"
              ? "Osoba ma link do formularza raportu."
              : "Raport przesłany; zamknij, gdy przeczytasz."}
          </span>
        </div>
      {/if}

      {#if detail.report}
        <section aria-labelledby="rep-h">
          <h3 class="h3" id="rep-h">
            Raport wolontariusza
            <span class="font-normal text-hm-ink-soft">
              · {when(detail.report.updated_at)}
            </span>
          </h3>
          <dl class="report">
            <div>
              <dt>Ile osób wzięło udział</dt>
              <dd class="tabular">{detail.report.participants}</dd>
            </div>
            <div>
              <dt>Czy poleca</dt>
              <dd>{recommendLabel[detail.report.recommend]}</dd>
            </div>
            {#each reportFields as f (f.key)}
              <div class="wide">
                <dt>{f.label}</dt>
                <dd class="whitespace-pre-line">
                  {nbsp(detail.report[f.key])}
                </dd>
              </div>
            {/each}
          </dl>
        </section>
      {/if}

      {#if detail.messages.length > 0}
        <section aria-labelledby="msg-h">
          <h3 class="h3" id="msg-h">Korespondencja</h3>
          <ol class="thread">
            {#each detail.messages as m (m.id)}
              <li>
                <span class="text-hm-ink-soft text-xs">
                  <b class="font-semibold text-hm-ink"
                    >{messageKind[m.kind]}{m.admin ? ` · ${m.admin}` : ""}</b
                  >
                  · {when(m.created_at)} · {deliveryWord[m.delivery_status]}
                </span>
                <p class="whitespace-pre-line text-sm">{m.body}</p>
              </li>
            {/each}
          </ol>
        </section>
      {/if}

      <form class="grid gap-1.5" onsubmit={send}>
        <h3 class="h3">
          <label for="volunteer-message">Napisz do tej osoby</label>
        </h3>
        <div class="reply">
          <textarea
            id="volunteer-message"
            maxlength="5000"
            onkeydown={keydown}
            placeholder="Wiadomość pójdzie e-mailem na {detail.email}. Odpowiedź przyjdzie do skrzynki ROPS."
            rows="4"
            bind:value={body}
          ></textarea>
          <div
            class="flex items-center justify-between gap-2.5 py-1.5 pr-1.5 pl-3.5 text-hm-ink-soft text-xs"
          >
            <span class="max-[899px]:hidden"
              ><kbd>Ctrl</kbd> <kbd>Enter</kbd> wyślij</span
            >
            <span class="relative ml-auto flex items-center gap-3">
              {#if stamp}
                <span
                  class={["sent", stamp, "hm-land stamp-word"]}
                  role="status"
                  >{stampWords[stamp]}</span
                >
              {/if}
              <button
                class="primary cladd-clickable"
                disabled={busy}
                type="submit"
              >
                <span>{busy ? "Wysyłanie…" : "Wyślij wiadomość"}</span>
              </button>
            </span>
          </div>
        </div>
      </form>
    </div>
  {:else if loadError}
    <ErrorState error={loadError} retry={() => load(id)} />
  {:else}
    <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
  {/if}
</article>

<style>
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

  .state {
    font-weight: 600;
    color: var(--hm-ink);
  }

  .st-new {
    color: var(--hm-stamp);
  }

  .st-accepted,
  .st-reported {
    color: var(--hm-ok);
  }

  .st-rejected {
    color: var(--hm-bad);
  }

  .who {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 20px;
    padding: 12px 14px;
    margin: 0;
    font-size: 13px;
    background: var(--hm-sunk);
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .who dt,
  .report dt {
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .who dd,
  .report dd {
    margin: 2px 0 0;
    font-weight: 560;
  }

  .report {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 20px;
    margin: 0;
    font-size: 14px;
  }

  .report .wide {
    grid-column: 1 / -1;
  }

  .report .wide dd {
    font-weight: 400;
    line-height: 1.5;
  }

  .h3 {
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 650;
  }

  .quote {
    padding-left: 12px;
    font-size: 15px;
    line-height: 1.5;
    text-wrap: pretty;
    white-space: pre-line;
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

  .field {
    height: 36px;
    padding: 0 12px;
    font-size: 14px;
    background: var(--hm-sunk);
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .field:focus-visible {
    outline: none;
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
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

  .reply {
    background: var(--hm-sunk);
    border-radius: 14px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .reply:focus-within {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .reply textarea {
    display: block;
    width: 100%;
    min-height: 100px;
    resize: vertical;
    border: 0;
    background: none;
    outline: none;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.5;
    field-sizing: content;
  }

  .reply textarea::placeholder {
    color: var(--hm-ink-soft);
  }

  kbd {
    padding: 3px 5px;
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--hm-board);
    border-radius: 5px;
    box-shadow: var(--shadow-cladd-cut-outline);
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

  .sent {
    padding: 2px 8px;
    color: var(--hm-ok);
    border: 2px solid currentColor;
    border-radius: 6px;
    rotate: -4deg;
  }

  .sent.failed {
    color: var(--hm-bad);
  }

  .sent.saved {
    color: var(--hm-ink-soft);
  }

  @media (max-width: 899px) {
    .sheet {
      padding: 16px;
      border-radius: 18px;
    }

    .back {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      justify-self: start;
      min-height: 44px;
      padding: 0 10px 0 4px;
      font-size: 14px;
      font-weight: 500;
      border-radius: 10px;
    }

    .primary,
    .ghost {
      height: 44px;
    }

    .who,
    .report {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
