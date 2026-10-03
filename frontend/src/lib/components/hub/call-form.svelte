<script lang="ts">
  import { untrack } from "svelte";
  import {
    type AdminGrantCall,
    type CallBody,
    createGrantCall,
    type GrantSection,
    type GrantTemplate,
    grantTemplates,
    patchGrantCall,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { blankSection, fromLocalInput, toLocalInput } from "$lib/grants";
  import { showTip } from "$lib/tip";

  const BODY_PREFIX = /^body\./;

  let {
    call,
    onsaved,
  }: {
    call: AdminGrantCall | null;
    onsaved: (call: AdminGrantCall) => void;
  } = $props();

  interface Draft {
    closes: string;
    description: string;
    opens: string;
    sections: GrantSection[];
    source: string;
    title: string;
  }

  const empty = (): Draft => {
    const now = new Date();
    const later = new Date(now.getTime() + 30 * 86_400_000);
    return {
      closes: toLocalInput(later.toISOString()),
      description: "",
      opens: toLocalInput(now.toISOString()),
      sections: [],
      source: "",
      title: "",
    };
  };

  const fromCall = (c: AdminGrantCall): Draft => ({
    closes: toLocalInput(c.closes_at),
    description: c.description,
    opens: toLocalInput(c.opens_at),
    sections: c.sections.map((s) => ({ ...s })),
    source: c.source_url ?? "",
    title: c.title,
  });

  let draft = $state<Draft>(empty());
  let templates = $state<GrantTemplate[]>([]);
  let saving = $state(false);
  let errors = $state<Record<string, string>>({});
  let formError = $state<string | null>(null);
  let template = $state<string | null>(null);

  $effect(() => {
    const source = call;
    untrack(() => {
      draft = source ? fromCall(source) : empty();
      errors = {};
      formError = null;
      template = source?.template ?? null;
    });
  });

  $effect(() => {
    grantTemplates()
      .then((t) => {
        templates = t;
      })
      .catch(() => {
        templates = [];
      });
  });

  const keys = $derived(new Set(draft.sections.map((s) => s.key)));
  const locked = $derived((call?.applications.total ?? 0) > 0);

  function loadTemplate(t: GrantTemplate, event: MouseEvent) {
    draft.sections = t.sections.map((s) => ({ ...s }));
    if (!draft.title.trim()) {
      draft.title = t.title;
    }
    if (!draft.description.trim()) {
      draft.description = t.description;
    }
    if (!draft.source.trim()) {
      draft.source = t.source_url;
    }
    template = t.slug;
    showTip(event.currentTarget as HTMLElement, "Wczytano szablon");
  }

  function move(index: number, step: number) {
    const next = [...draft.sections];
    const [item] = next.splice(index, 1);
    next.splice(index + step, 0, item);
    draft.sections = next;
  }

  function remove(index: number) {
    draft.sections = draft.sections.filter((_, i) => i !== index);
  }

  function add() {
    draft.sections = [...draft.sections, blankSection(keys)];
    requestAnimationFrame(() => {
      document
        .querySelector<HTMLInputElement>(
          `#section-label-${draft.sections.length - 1}`
        )
        ?.focus();
    });
  }

  function fieldErrors(e: ApiError) {
    const out: Record<string, string> = {};
    const body = e.body as {
      detail?: { fields?: { field: string; message: string }[] };
    } | null;
    for (const f of body?.detail?.fields ?? []) {
      out[f.field.replace(BODY_PREFIX, "")] = f.message;
    }
    return out;
  }

  async function save(event: SubmitEvent) {
    event.preventDefault();
    const button = event.submitter as HTMLElement | null;
    if (saving) {
      return;
    }
    saving = true;
    errors = {};
    formError = null;
    const body: CallBody = {
      closes_at: fromLocalInput(draft.closes),
      description: draft.description.trim(),
      opens_at: fromLocalInput(draft.opens),
      sections: draft.sections.map((s) => ({
        ...s,
        hint: s.hint.trim(),
        label: s.label.trim(),
        max_length: Number(s.max_length),
      })),
      source_url: draft.source.trim() || null,
      title: draft.title.trim(),
    };
    try {
      const saved = call
        ? await patchGrantCall(call.id, body)
        : await createGrantCall({
            ...body,
            source_url: body.source_url ?? undefined,
            template: template ?? undefined,
          });
      showTip(button, call ? "Zapisano" : "Utworzono szkic");
      onsaved(saved);
    } catch (e) {
      if (e instanceof ApiError) {
        errors = fieldErrors(e);
        formError = e.message;
      } else {
        formError = "Brak połączenia z serwerem.";
      }
      showTip(button, "Nie zapisano", "bad");
    } finally {
      saving = false;
    }
  }

  const err = (key: string) => errors[key] ?? null;
  const idleLabel = $derived(call ? "Zapisz zmiany" : "Utwórz szkic naboru");
  const submitLabel = $derived(saving ? "Zapisywanie…" : idleLabel);
</script>

<form class="form" novalidate onsubmit={save}>
  <div class="grid gap-4">
    {#if !call && templates.length > 0}
      <div class="template">
        {#each templates as t (t.slug)}
          <button
            class="ghost cladd-clickable"
            onclick={(event) => loadTemplate(t, event)}
            type="button"
          >
            <span>Wczytaj szablon ROPS</span>
          </button>
          <span class="text-hm-ink-soft text-xs">{t.title}</span>
        {/each}
      </div>
    {/if}

    <label class="field">
      <span class="label">Tytuł naboru</span>
      <input
        aria-invalid={err("title") ? "true" : undefined}
        maxlength="200"
        required
        bind:value={draft.title}
      >
      {#if err("title")}
        <span class="error">{err("title")}</span>
      {/if}
    </label>

    <label class="field">
      <span class="label">Opis dla mieszkańców</span>
      <textarea
        aria-invalid={err("description") ? "true" : undefined}
        maxlength="10000"
        rows="5"
        bind:value={draft.description}
      ></textarea>
      {#if err("description")}
        <span class="error">{err("description")}</span>
      {/if}
    </label>

    <div class="pair">
      <label class="field">
        <span class="label">Otwarcie</span>
        <input
          aria-invalid={err("opens_at") ? "true" : undefined}
          type="datetime-local"
          bind:value={draft.opens}
        >
        {#if err("opens_at")}
          <span class="error">{err("opens_at")}</span>
        {/if}
      </label>
      <label class="field">
        <span class="label">Zamknięcie</span>
        <input
          aria-invalid={err("closes_at") ? "true" : undefined}
          type="datetime-local"
          bind:value={draft.closes}
        >
        {#if err("closes_at")}
          <span class="error">{err("closes_at")}</span>
        {/if}
      </label>
    </div>

    <label class="field">
      <span class="label">Strona naboru w&nbsp;ROPS</span>
      <input
        aria-invalid={err("source_url") ? "true" : undefined}
        inputmode="url"
        placeholder="https://rops.krakow.pl/…"
        type="url"
        bind:value={draft.source}
      >
      {#if err("source_url")}
        <span class="error">{err("source_url")}</span>
      {/if}
    </label>
  </div>

  <fieldset class="sections">
    <legend class="font-semibold text-sm">
      Sekcje wniosku
      <span class="font-medium text-hm-ink-soft tabular"
        >{draft.sections.length}</span
      >
    </legend>
    {#if locked}
      <p class="text-hm-ink-soft text-xs">
        Nabór ma już wnioski: możesz zmieniać nazwy, podpowiedzi i limity, ale
        nie dodawać ani usuwać sekcji.
      </p>
    {/if}
    {#if err("sections")}
      <p class="error">{err("sections")}</p>
    {/if}
    {#if draft.sections.length === 0}
      <p class="text-[13px] text-hm-ink-soft">
        Brak sekcji. Wczytaj szablon ROPS albo dodaj własną.
      </p>
    {/if}
    <ol>
      {#each draft.sections as s, i (s.key)}
        <li>
          <span class="mono-num n text-hm-stamp">{i + 1}</span>
          <div class="grid min-w-0 gap-2">
            <label class="field">
              <span class="sr-only">Nazwa sekcji {i + 1}</span>
              <input
                aria-invalid={err(`sections.${i}.label`) ? "true" : undefined}
                class="strong"
                id="section-label-{i}"
                maxlength="200"
                placeholder="Nazwa sekcji"
                bind:value={s.label}
              >
            </label>
            <label class="field">
              <span class="sr-only">Podpowiedź do sekcji {i + 1}</span>
              <textarea
                maxlength="1000"
                placeholder="Pytania pomocnicze dla autora"
                rows="2"
                bind:value={s.hint}
              ></textarea>
            </label>
            <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
              <label class="inline">
                <span class="text-hm-ink-soft text-xs">Limit znaków</span>
                <input
                  class="num"
                  max="10000"
                  min="100"
                  step="100"
                  type="number"
                  bind:value={s.max_length}
                >
              </label>
              <label class="inline">
                <input type="checkbox" bind:checked={s.required}>
                <span class="text-xs">Obowiązkowa</span>
              </label>
              <span class="tools">
                <button
                  aria-label="Przesuń sekcję {i + 1} wyżej"
                  disabled={i === 0}
                  onclick={() => move(i, -1)}
                  type="button"
                >
                  <svg
                    aria-hidden="true"
                    fill="none"
                    height="16"
                    stroke="currentColor"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.75"
                    viewBox="0 0 24 24"
                    width="16"
                  >
                    <path d="m6 15 6-6 6 6" />
                  </svg>
                </button>
                <button
                  aria-label="Przesuń sekcję {i + 1} niżej"
                  disabled={i === draft.sections.length - 1}
                  onclick={() => move(i, 1)}
                  type="button"
                >
                  <svg
                    aria-hidden="true"
                    fill="none"
                    height="16"
                    stroke="currentColor"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="1.75"
                    viewBox="0 0 24 24"
                    width="16"
                  >
                    <path d="m6 9 6 6 6-6" />
                  </svg>
                </button>
                {#if !locked}
                  <button
                    aria-label="Usuń sekcję {i + 1}"
                    class="bad"
                    onclick={() => remove(i)}
                    type="button"
                  >
                    <svg
                      aria-hidden="true"
                      fill="none"
                      height="16"
                      stroke="currentColor"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="1.75"
                      viewBox="0 0 24 24"
                      width="16"
                    >
                      <path d="M6 6l12 12M18 6 6 18" />
                    </svg>
                  </button>
                {/if}
              </span>
            </div>
          </div>
        </li>
      {/each}
    </ol>
    {#if !locked}
      <button class="ghost cladd-clickable add" onclick={add} type="button">
        <span>Dodaj sekcję</span>
      </button>
    {/if}
  </fieldset>

  <div class="foot">
    {#if formError}
      <p class="error" role="alert">{formError}</p>
    {/if}
    <button class="primary cladd-clickable" disabled={saving} type="submit">
      <span>
        {submitLabel}
      </span>
    </button>
  </div>
</form>

<style>
  .form {
    display: grid;
    gap: 24px;
    max-width: 720px;
  }

  .template {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 12px;
    align-items: center;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--hm-rule);
  }

  .field {
    display: grid;
    gap: 6px;
  }

  .label {
    font-size: 13px;
    font-weight: 600;
  }

  .pair {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  input:not([type="checkbox"]),
  textarea {
    width: 100%;
    min-height: 38px;
    padding: 8px 12px;
    font-size: 14px;
    color: var(--hm-ink);
    outline: none;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 10px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  textarea {
    resize: vertical;
    line-height: 1.5;
    field-sizing: content;
  }

  input:focus,
  textarea:focus {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  input[aria-invalid="true"],
  textarea[aria-invalid="true"] {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-bad),
      var(--shadow-cladd-cut-outline);
  }

  input::placeholder,
  textarea::placeholder {
    color: var(--hm-ink-soft);
  }

  input.strong {
    font-weight: 600;
  }

  input.num {
    width: 96px;
    min-height: 32px;
    padding: 4px 8px;
    font-variant-numeric: tabular-nums;
  }

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--hm-stamp);
  }

  .inline {
    display: inline-flex;
    gap: 8px;
    align-items: center;
  }

  .error {
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-bad);
  }

  .sections {
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 0;
    margin: 0;
    border: 0;
  }

  .sections legend {
    margin-bottom: 10px;
  }

  .sections ol {
    padding: 0;
    margin: 0;
    list-style: none;
    border-top: 1px solid var(--hm-rule);
  }

  .sections li {
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr);
    gap: 10px;
    padding: 14px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .n {
    padding-top: 9px;
    font-size: 13px;
    font-weight: 600;
  }

  .tools {
    display: inline-flex;
    gap: 2px;
    margin-left: auto;
  }

  .tools button {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    color: var(--hm-ink-soft);
    border-radius: 9px;
    transition:
      background-color 150ms ease,
      color 150ms ease;
  }

  .tools button:hover:not(:disabled) {
    color: var(--hm-ink);
    background: var(--hm-sunk);
  }

  .tools button.bad:hover {
    color: var(--hm-bad);
  }

  .tools button:disabled {
    opacity: 0.4;
  }

  .ghost {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-self: start;
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

  .foot {
    position: sticky;
    bottom: -30px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    justify-content: flex-end;
    padding: 14px 0 4px;
    background: linear-gradient(to bottom, transparent, var(--hm-paper) 30%);
  }

  .foot .error {
    margin-right: auto;
  }

  .primary {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 38px;
    padding: 0 16px;
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

  @media (max-width: 899px) {
    .pair {
      grid-template-columns: minmax(0, 1fr);
    }

    input:not([type="checkbox"]),
    .ghost,
    .primary,
    .tools button {
      min-height: 44px;
    }

    .tools button {
      width: 44px;
    }

    .foot {
      bottom: -16px;
    }
  }
</style>
