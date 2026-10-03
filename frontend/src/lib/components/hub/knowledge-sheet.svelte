<script lang="ts">
  import {
    type AdminChallenge,
    type AdminMaterial,
    patchChallenge,
    patchMaterial,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { when } from "$lib/format";
  import { showTip } from "$lib/tip";

  type Item =
    | { kind: "challenge"; value: AdminChallenge }
    | { kind: "material"; value: AdminMaterial };

  let {
    item,
    backHref,
    onsaved,
  }: {
    item: Item;
    backHref: string;
    onsaved: (next: Item) => void;
  } = $props();

  let title = $state("");
  let summary = $state("");
  let description = $state("");
  let saving = $state(false);
  let lastId = "";

  $effect(() => {
    const { id: nextId, summary: nextSummary, title: nextTitle } = item.value;
    if (nextId !== lastId) {
      lastId = nextId;
      title = nextTitle;
      summary = nextSummary ?? "";
      description = item.kind === "challenge" ? item.value.description : "";
    }
  });

  const changed = $derived.by(() => {
    const body: Record<string, string> = {};
    if (title.trim() !== item.value.title) {
      body.title = title.trim();
    }
    if (summary.trim() !== (item.value.summary ?? "").trim()) {
      body.summary = summary.trim();
    }
    if (
      item.kind === "challenge" &&
      description.trim() !== item.value.description.trim()
    ) {
      body.description = description.trim();
    }
    return body;
  });

  const changeCount = $derived(Object.keys(changed).length);

  async function patch(body: Record<string, unknown>): Promise<Item> {
    if (item.kind === "challenge") {
      return {
        kind: "challenge",
        value: await patchChallenge(item.value.id, body),
      };
    }
    return {
      kind: "material",
      value: await patchMaterial(item.value.id, body),
    };
  }

  async function run(
    body: Record<string, unknown>,
    button: HTMLElement | null,
    done: string
  ) {
    saving = true;
    try {
      const next = await patch(body);
      lastId = "";
      onsaved(next);
      showTip(button, done);
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się zapisać.",
        "bad"
      );
    } finally {
      saving = false;
    }
  }

  function save(event: SubmitEvent) {
    event.preventDefault();
    const button = document.getElementById("save-knowledge");
    if (changeCount === 0) {
      showTip(button, "Nic się nie zmieniło");
      return;
    }
    run(changed, button, "Zapisano");
  }

  const size = (bytes: number | null) =>
    bytes
      ? `${(bytes / 1_048_576).toLocaleString("pl-PL", { maximumFractionDigits: 1 })} MB`
      : "";
</script>

<article aria-labelledby="k-title" class="sheet">
  <form class="grid max-w-[680px] gap-5" onsubmit={save}>
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
      Wiedza
    </a>
    <header class="grid gap-1.5">
      <label class="sr-only" for="k-title-input">Tytuł</label>
      <textarea
        class="title"
        id="k-title-input"
        required
        rows="1"
        bind:value={title}
      ></textarea>
      <p class="text-[13px] text-hm-ink-soft" id="k-title">
        {#if item.kind === "challenge"}
          {item.value.area.name}
          · {item.value.status === "published" ? "opublikowane" : "szkic"} ·
          {#if item.value.verified}
            sprawdzone przez
            {item.value.verified_by ?? "ROPS"}{item.value.verified_at ? ` ${when(item.value.verified_at)}` : ""}
          {:else}
            opracowanie automatyczne, jeszcze niesprawdzone
          {/if}
        {:else}
          {item.value.kind.name}{item.value.year ? `, ${item.value.year}` : ""}
          · {item.value.status === "published" ? "opublikowany" : "szkic"}
          {#if item.value.summary_ai}
            · streszczenie przygotowane automatycznie
          {/if}
        {/if}
      </p>
    </header>

    <div class="grid gap-1.5">
      <label class="font-semibold text-[13px]" for="k-summary"
        >{item.kind === "challenge" ? "W jednym zdaniu" : "Streszczenie"}</label
      >
      <textarea
        class="well"
        id="k-summary"
        rows={item.kind === "challenge" ? 2 : 5}
        bind:value={summary}
      ></textarea>
    </div>

    {#if item.kind === "challenge"}
      <div class="grid gap-1.5">
        <label class="font-semibold text-[13px]" for="k-description"
          >Opis</label
        >
        <textarea
          class="well"
          id="k-description"
          rows="7"
          bind:value={description}
        ></textarea>
      </div>

      {#if item.value.figures.length > 0}
        <section aria-labelledby="fig-h">
          <h3 class="mb-1.5 font-semibold text-[13px]" id="fig-h">
            Liczby z&nbsp;dokumentu
          </h3>
          <ul class="figs">
            {#each item.value.figures as f, i (i)}
              <li>
                <span class="tabular font-semibold text-lg">{f.value}</span>
                <span class="text-sm"
                  >{f.label}{f.year ? `, ${f.year}` : ""}
                  ({f.scope === "Polska" ? "dane dla całej Polski" : f.scope})</span
                >
                <a
                  class="link text-xs"
                  href="{f.document_url}#page={f.page}"
                  rel="noopener"
                  target="_blank"
                  >Źródło: {f.document_title}, s. {f.page}</a
                >
              </li>
            {/each}
          </ul>
        </section>
      {/if}
      <p class="text-[13px]">
        <a
          class="link"
          href="{item.value.source.url}{item.value.source.pages[0] ? `#page=${item.value.source.pages[0]}` : ''}"
          rel="noopener"
          target="_blank"
          >Źródło:
          {item.value.source.title}{item.value.source.pages.length ? `, s. ${item.value.source.pages.join(", ")}` : ""}</a
        >
      </p>
    {:else}
      {#if item.value.topics.length > 0}
        <p class="text-[13px] text-hm-ink-soft">
          Tematy: {item.value.topics.map((t) => t.name).join(", ")}
        </p>
      {/if}
      <p class="text-[13px]">
        <a
          class="link"
          href={item.value.file_url}
          rel="noopener"
          target="_blank"
          >Pobierz PDF z&nbsp;ROPS</a
        >
        <span class="text-hm-ink-soft"
          >{[item.value.pages ? `${item.value.pages} s.` : "", size(item.value.file_size)].filter(Boolean).join(", ")}</span
        >
      </p>
    {/if}

    <div class="foot">
      <span class="flex flex-wrap gap-2">
        {#if item.kind === "challenge"}
          <button
            class="ghost cladd-clickable"
            disabled={saving}
            onclick={(event) => run({ verified: item.kind === "challenge" && !item.value.verified }, event.currentTarget, "Zapisano")}
            type="button"
          >
            <span
              >{item.value.verified ? "Cofnij sprawdzenie" : "Oznacz jako sprawdzone"}</span
            >
          </button>
        {/if}
        <button
          class="ghost cladd-clickable"
          disabled={saving}
          onclick={(event) =>
            run({ status: item.value.status === "published" ? "draft" : "published" }, event.currentTarget, item.value.status === "published" ? "Ukryto" : "Opublikowano")}
          type="button"
        >
          <span
            >{item.value.status === "published" ? "Ukryj" : "Opublikuj"}</span
          >
        </button>
      </span>
      <button
        class="primary cladd-clickable"
        disabled={saving}
        id="save-knowledge"
        type="submit"
      >
        <span
          >{changeCount > 0 ? `Zapisz zmiany (${changeCount})` : "Zapisz"}</span
        >
      </button>
    </div>
  </form>
</article>

<style>
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

  .title {
    display: block;
    resize: none;
    field-sizing: content;
    line-height: 1.25;
    width: 100%;
    padding: 2px 0;
    font-size: 22px;
    font-weight: 650;
    letter-spacing: -0.02em;
    outline: none;
    background: none;
    border: 0;
  }

  .title:focus-visible {
    box-shadow: 0 2px 0 var(--hm-ring);
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

  .well:focus {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .figs {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .figs li {
    display: grid;
    gap: 2px;
    padding: 10px 0;
    border-bottom: 1px dashed var(--hm-rule);
  }

  .figs li:last-child {
    border-bottom: 0;
  }

  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .foot {
    position: sticky;
    bottom: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    padding: 14px 0 20px;
    background: linear-gradient(to top, var(--hm-paper) 75%, transparent);
  }

  .primary,
  .ghost {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 14px;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
    border-radius: 10px;
    transition: background-color 150ms ease;
  }

  .primary {
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

  .ghost {
    color: var(--hm-ink);
    background: var(--hm-sunk);
    box-shadow: var(--shadow-cladd-outline);
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  .primary:disabled,
  .ghost:disabled {
    opacity: 0.6;
  }

  @media (max-width: 899px) {
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

    .primary,
    .ghost {
      height: 44px;
    }
  }
</style>
