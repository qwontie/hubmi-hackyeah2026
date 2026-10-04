<script lang="ts">
  import { type AdminMaterial, patchMaterial } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { showTip } from "$lib/tip";

  let {
    item,
    backHref,
    onsaved,
  }: {
    item: AdminMaterial;
    backHref: string;
    onsaved: (next: AdminMaterial) => void;
  } = $props();

  let title = $state("");
  let summary = $state("");
  let saving = $state(false);
  let lastId = "";

  $effect(() => {
    const { id: nextId, summary: nextSummary, title: nextTitle } = item;
    if (nextId !== lastId) {
      lastId = nextId;
      title = nextTitle;
      summary = nextSummary ?? "";
    }
  });

  const changed = $derived.by(() => {
    const body: Record<string, string> = {};
    if (title.trim() !== item.title) {
      body.title = title.trim();
    }
    if (summary.trim() !== (item.summary ?? "").trim()) {
      body.summary = summary.trim();
    }
    return body;
  });

  const changeCount = $derived(Object.keys(changed).length);

  async function run(
    body: Record<string, unknown>,
    button: HTMLElement | null,
    done: string
  ) {
    saving = true;
    try {
      const next = await patchMaterial(item.id, body);
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
    const button = document.getElementById("save-material");
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

<article aria-labelledby="m-title" class="sheet">
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
      Materiały
    </a>
    <header class="grid gap-1.5">
      <label class="sr-only" for="m-title-input">Tytuł</label>
      <textarea
        class="title"
        id="m-title-input"
        required
        rows="1"
        bind:value={title}
      ></textarea>
      <p class="text-[13px] text-hm-ink-soft" id="m-title">
        {item.kind.name}{item.year ? `, ${item.year}` : ""}
        · {item.status === "published" ? "opublikowany" : "szkic"}
        {#if item.summary_ai}
          · streszczenie przygotowane automatycznie
        {/if}
      </p>
    </header>

    <div class="grid gap-1.5">
      <label class="font-semibold text-[13px]" for="m-summary"
        >Streszczenie</label
      >
      <textarea
        class="well"
        id="m-summary"
        rows="5"
        bind:value={summary}
      ></textarea>
    </div>

    {#if item.topics.length > 0}
      <p class="text-[13px] text-hm-ink-soft">
        Tematy: {item.topics.map((t) => t.name).join(", ")}
      </p>
    {/if}
    <p class="text-[13px]">
      <a class="link" href={item.file_url} rel="noopener" target="_blank"
        >Pobierz PDF z&nbsp;ROPS</a
      >
      <span class="text-hm-ink-soft"
        >{[item.pages ? `${item.pages} s.` : "", size(item.file_size)].filter(Boolean).join(", ")}</span
      >
    </p>

    <div class="foot">
      <button
        class="ghost cladd-clickable"
        disabled={saving}
        onclick={(event) =>
          run({ status: item.status === "published" ? "draft" : "published" }, event.currentTarget, item.status === "published" ? "Ukryto" : "Opublikowano")}
        type="button"
      >
        <span
          >{item.status === "published" ? "Ukryj przed mieszkańcami" : "Opublikuj"}</span
        >
      </button>
      <button
        class="primary cladd-clickable"
        disabled={saving}
        id="save-material"
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
