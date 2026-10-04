<script lang="ts">
  import { tick } from "svelte";
  import { type AdminVolunteer, writeToVolunteer } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { plural, when } from "$lib/format";
  import { contactKey, whoLabel } from "$lib/opinions";
  import { showTip } from "$lib/tip";
  import { deliveryWord, volunteerLabel } from "$lib/volunteers";

  type Row = AdminVolunteer & { last_contact_at?: string | null };

  interface Person {
    apps: Row[];
    email: string;
    key: string;
    last: string;
    latest: Row;
    reports: number;
  }

  let {
    rows,
    matched,
    appHref,
    onwritten,
  }: {
    rows: Row[];
    matched: Row[];
    appHref: (id: string) => string;
    onwritten: () => void;
  } = $props();

  let dialog = $state<HTMLDialogElement | null>(null);
  let writing = $state<Person | null>(null);
  let about = $state("");
  let body = $state("");
  let busy = $state(false);
  let opener: HTMLElement | null = null;

  const stamp = (iso: string | null | undefined) =>
    iso ? new Date(iso).getTime() : 0;

  function lastContact(r: Row): string {
    const times = [
      r.created_at,
      r.last_contact_at ?? null,
      r.decided_at,
      r.report?.updated_at ?? null,
    ].filter((t): t is string => Boolean(t));
    return times.reduce((a, b) => (stamp(b) > stamp(a) ? b : a));
  }

  const people = $derived.by(() => {
    const wanted = new Set(matched.map((r) => contactKey(r.email)));
    const byKey = new Map<string, Row[]>();
    for (const r of rows) {
      const key = contactKey(r.email);
      if (wanted.has(key)) {
        byKey.set(key, [...(byKey.get(key) ?? []), r]);
      }
    }
    const out: Person[] = [];
    for (const [key, list] of byKey) {
      const apps = [...list].sort(
        (a, b) => stamp(b.created_at) - stamp(a.created_at)
      );
      const last = apps
        .map(lastContact)
        .reduce((a, b) => (stamp(b) > stamp(a) ? b : a));
      out.push({
        apps,
        email: apps[0].email,
        key,
        last,
        latest: apps[0],
        reports: apps.filter((a) => a.report).length,
      });
    }
    return out.sort((a, b) => stamp(b.last) - stamp(a.last));
  });

  function reportWord(p: Person): string {
    if (p.reports === 0) {
      return "nie";
    }
    return p.apps.length === 1 ? "tak" : `${p.reports} z ${p.apps.length}`;
  }

  async function copyAll(event: MouseEvent) {
    const button = event.currentTarget as HTMLElement;
    const emails = people.map((p) => p.email);
    try {
      await navigator.clipboard.writeText(emails.join(", "));
      showTip(
        button,
        `Skopiowano ${emails.length} ${plural(emails.length, "adres", "adresy", "adresów")}`
      );
    } catch {
      showTip(button, "Przeglądarka nie pozwoliła skopiować.", "bad");
    }
  }

  async function open(person: Person, event: MouseEvent) {
    opener = event.currentTarget as HTMLElement;
    writing = person;
    about = person.latest.id;
    body = "";
    await tick();
    dialog?.showModal();
  }

  function closed() {
    writing = null;
    opener?.focus();
  }

  async function send(event: SubmitEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const anchor = form.querySelector<HTMLElement>("button[type=submit]");
    const text = body.trim();
    if (text.length < 2) {
      showTip(anchor, "Najpierw napisz wiadomość.", "bad");
      return;
    }
    busy = true;
    try {
      const message = await writeToVolunteer(about, text);
      const target = opener;
      dialog?.close();
      showTip(
        target,
        `Wiadomość zapisana, ${deliveryWord[message.delivery_status]}`,
        message.delivery_status === "failed" ? "bad" : "ink"
      );
      onwritten();
    } catch (e) {
      showTip(
        anchor,
        e instanceof ApiError ? e.message : "Brak połączenia z serwerem.",
        "bad"
      );
    } finally {
      busy = false;
    }
  }

  function keydown(event: KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      (event.currentTarget as HTMLTextAreaElement).form?.requestSubmit();
    }
  }
</script>

<div class="bar">
  <span aria-live="polite" class="tabular">
    {people.length}
    {plural(people.length, "osoba", "osoby", "osób")}
  </span>
  <button
    class="ghost cladd-clickable"
    disabled={people.length === 0}
    onclick={copyAll}
    type="button"
  >
    <span>Kopiuj widoczne adresy e-mail</span>
  </button>
</div>

{#if people.length === 0}
  <p class="px-3 py-6 text-hm-ink-soft text-sm">
    {rows.length === 0 ? "Nikt jeszcze nie zgłosił się jako wolontariusz." : "Nikt nie pasuje do filtrów."}
  </p>
{:else}
  <table class="people">
    <caption class="sr-only">
      Wolontariusze, jedna osoba w&nbsp;wierszu, ostatni kontakt na górze
    </caption>
    <thead>
      <tr>
        <th scope="col">Osoba</th>
        <th scope="col">Powiat</th>
        <th scope="col">Zgłoszenia i&nbsp;stan</th>
        <th scope="col">Raport</th>
        <th scope="col">Ostatni kontakt</th>
        <th scope="col"><span class="sr-only">Działania</span></th>
      </tr>
    </thead>
    <tbody>
      {#each people as p (p.key)}
        <tr>
          <th class="who" scope="row">
            <span class="grid gap-[3px]">
              <span class="email">{p.email}</span>
              <span class="text-hm-ink-soft text-xs">
                {[whoLabel[p.latest.who], p.latest.organization]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            </span>
          </th>
          <td class="nowrap" data-label="Powiat">{p.latest.powiat_name}</td>
          <td>
            <ul class="apps">
              {#each p.apps as a (a.id)}
                <li>
                  <a class="link" href={appHref(a.id)}>{a.innovation.title}</a>
                  <span class={["st", `is-${a.status}`]}
                    >{volunteerLabel[a.status]}</span
                  >
                </li>
              {/each}
            </ul>
          </td>
          <td data-label="Raport">{reportWord(p)}</td>
          <td class="nowrap tabular" data-label="Ostatni kontakt">
            {when(p.last)}
          </td>
          <td class="act">
            <button
              aria-label="Napisz do {p.email}"
              class="ghost cladd-clickable"
              onclick={(event) => open(p, event)}
              type="button"
            >
              <span>Napisz</span>
            </button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{/if}

<dialog
  aria-labelledby="write-title"
  class="composer"
  onclose={closed}
  bind:this={dialog}
>
  {#if writing}
    <form class="grid gap-3" onsubmit={send}>
      <h2 class="font-semibold text-lg" id="write-title">
        Napisz do {writing.email}
      </h2>
      {#if writing.apps.length > 1}
        <label class="grid gap-1.5">
          <span class="font-semibold text-[13px]">W sprawie zgłoszenia</span>
          <select class="well h-10" bind:value={about}>
            {#each writing.apps as a (a.id)}
              <option value={a.id}>
                {a.innovation.title}
                ({volunteerLabel[a.status].toLocaleLowerCase("pl")})
              </option>
            {/each}
          </select>
        </label>
      {:else}
        <p class="text-[13px] text-hm-ink-soft">
          W sprawie: {writing.apps[0].innovation.title}
        </p>
      {/if}
      <label class="grid gap-1.5">
        <span class="font-semibold text-[13px]">Wiadomość</span>
        <textarea
          class="well"
          maxlength="5000"
          onkeydown={keydown}
          placeholder="Pójdzie e-mailem przez pocztę HubMi. Odpowiedź przyjdzie do skrzynki ROPS."
          rows="6"
          bind:value={body}
        ></textarea>
      </label>
      <div class="flex items-center justify-end gap-2.5">
        <button
          class="ghost cladd-clickable"
          onclick={() => dialog?.close()}
          type="button"
        >
          <span>Anuluj</span>
        </button>
        <button class="primary cladd-clickable" disabled={busy} type="submit">
          <span>{busy ? "Wysyłanie…" : "Wyślij wiadomość"}</span>
        </button>
      </div>
    </form>
  {/if}
</dialog>

<style>
  .bar {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    padding: 8px 4px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .people {
    width: 100%;
    font-size: 14px;
    border-collapse: collapse;
  }

  .people thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    padding: 8px 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    text-align: left;
    background: var(--hm-board);
    border-bottom: 1px solid var(--hm-rule);
  }

  .people tbody th,
  .people td {
    padding: 11px 10px;
    vertical-align: top;
    text-align: left;
    border-bottom: 1px solid var(--hm-rule);
  }

  .people tbody tr:hover {
    background: color-mix(in oklab, var(--hm-stamp) 5%, transparent);
  }

  .who {
    min-width: 0;
    font-weight: 400;
  }

  .email {
    font-weight: 600;
    overflow-wrap: anywhere;
  }

  .apps {
    display: grid;
    gap: 4px;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .apps li {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 10px;
    align-items: baseline;
  }

  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
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

  .is-new {
    color: var(--hm-stamp);
  }

  .is-accepted,
  .is-reported {
    color: var(--hm-ok);
  }

  .is-rejected {
    color: var(--hm-bad);
  }

  .act {
    text-align: right;
  }

  .nowrap {
    white-space: nowrap;
  }

  .ghost,
  .primary {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    border-radius: 10px;
    transition: background-color 150ms ease;
  }

  .ghost {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  .ghost:disabled {
    color: var(--hm-ink-soft);
  }

  .primary {
    height: 36px;
    padding: 0 14px;
    color: var(--hm-on-stamp);
    background-color: var(--hm-stamp);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.16),
      transparent
    );
    box-shadow: var(--shadow-cladd-outline-fill);
  }

  .primary:hover {
    background-color: var(--hm-stamp-press);
  }

  .primary:disabled {
    opacity: 0.6;
  }

  .composer {
    width: min(560px, calc(100vw - 24px));
    padding: 26px 28px;
    margin: auto;
    color: var(--hm-ink);
    background: var(--hm-paper);
    border: 0;
    border-radius: 20px;
    box-shadow:
      0 24px 64px -12px oklch(0.2 0.04 280 / 0.18),
      0 0 0 1px var(--hm-rule);
  }

  .composer::backdrop {
    background: oklch(0.2 0.04 280 / 0.35);
  }

  .well {
    width: 100%;
    padding: 10px 12px;
    font-size: 14px;
    line-height: 1.5;
    outline: none;
    resize: vertical;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
    field-sizing: content;
  }

  .well:focus {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  textarea.well {
    min-height: 140px;
  }

  @media (max-width: 899px) {
    .people thead {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }

    .people,
    .people tbody,
    .people tr,
    .people tbody th,
    .people td {
      display: block;
    }

    .people tr {
      padding: 10px 4px;
      border-bottom: 1px solid var(--hm-rule);
    }

    .people tbody th,
    .people td {
      padding: 3px 4px;
      border: 0;
    }

    .people td[data-label]::before {
      margin-right: 6px;
      font-size: 12px;
      color: var(--hm-ink-soft);
      content: attr(data-label) ":";
    }

    .act {
      padding-top: 8px;
      text-align: left;
    }

    .ghost,
    .primary {
      height: 44px;
    }

    .composer {
      padding: 18px 16px;
    }
  }
</style>
