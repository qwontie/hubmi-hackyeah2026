<script lang="ts">
  import { onDestroy } from "svelte";
  import { resolve } from "$app/paths";
  import {
    addMaterial,
    type IngestJob,
    type IngestResult,
    ingestJob,
    uploadMaterial,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { live } from "$lib/live/stream.svelte";

  type Mode = "url" | "pdf" | "text";

  let { onclose }: { onclose: () => void } = $props();

  const modes: { id: Mode; label: string }[] = [
    { id: "url", label: "Link" },
    { id: "pdf", label: "Plik PDF" },
    { id: "text", label: "Tekst" },
  ];
  const steps: { id: NonNullable<IngestJob["step"]>; label: string }[] = [
    { id: "fetch", label: "Pobieranie" },
    { id: "text", label: "Odczyt tekstu" },
    { id: "summary", label: "Streszczenie" },
    { id: "save", label: "Zapis" },
    { id: "embedding", label: "Indeks wyszukiwania" },
  ];
  const MIN_TEXT = 400;
  const MAX_PDF = 30 * 1024 * 1024;

  let mode = $state<Mode>("url");
  let url = $state("");
  let title = $state("");
  let text = $state("");
  let file = $state<File | null>(null);
  let dragging = $state(false);
  let sending = $state(false);
  let job = $state<IngestJob | null>(null);
  let problem = $state<string | null>(null);
  let poll: ReturnType<typeof setInterval> | undefined;
  let fileInput = $state<HTMLInputElement | null>(null);

  const running = $derived(sending || job?.status === "running");
  const stepIndex = $derived(
    job?.step ? steps.findIndex((s) => s.id === job?.step) : -1
  );

  function track(next: IngestJob) {
    if (!job || next.job_id !== job.job_id) {
      return;
    }
    job = { ...job, ...next };
    if (next.status !== "running") {
      clearInterval(poll);
    }
  }

  const offs = [
    live.on("ingest.progress", (data) => track(data as IngestJob)),
    live.on("ingest.finished", (data) => track(data as IngestJob)),
  ];

  onDestroy(() => {
    clearInterval(poll);
    for (const off of offs) {
      off();
    }
  });

  function check(): string | null {
    if (mode === "url") {
      try {
        const parsed = new URL(url.trim());
        return parsed.protocol === "http:" || parsed.protocol === "https:"
          ? null
          : "Podaj adres zaczynający się od https://";
      } catch {
        return "Podaj pełny adres strony lub pliku PDF.";
      }
    }
    if (mode === "pdf") {
      if (!file) {
        return "Wybierz plik PDF.";
      }
      return file.size > MAX_PDF ? "Plik jest większy niż 30 MB." : null;
    }
    if (title.trim().length < 3) {
      return "Podaj tytuł materiału.";
    }
    return text.trim().length < MIN_TEXT
      ? `Wklej co najmniej ${MIN_TEXT} znaków tekstu.`
      : null;
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    problem = check();
    if (problem || running) {
      return;
    }
    sending = true;
    job = null;
    try {
      const started =
        mode === "pdf" && file
          ? await uploadMaterial(file, title.trim() || undefined)
          : await addMaterial(
              mode === "url"
                ? {
                    kind: "url",
                    title: title.trim() || undefined,
                    url: url.trim(),
                  }
                : { kind: "text", text: text.trim(), title: title.trim() }
            );
      job = { job_id: started.job_id, status: "running" };
      clearInterval(poll);
      poll = setInterval(() => {
        if (job?.status !== "running") {
          clearInterval(poll);
          return;
        }
        ingestJob(job.job_id)
          .then(track)
          .catch(() => undefined);
      }, 2000);
    } catch (e) {
      problem =
        e instanceof ApiError ? e.message : "Brak połączenia z serwerem.";
    } finally {
      sending = false;
    }
  }

  function pick(list: FileList | null | undefined) {
    const next = list?.[0] ?? null;
    if (next?.type && next.type !== "application/pdf") {
      problem = "To nie jest plik PDF.";
      return;
    }
    problem = null;
    file = next;
  }

  function again() {
    job = null;
    url = "";
    text = "";
    title = "";
    file = null;
    problem = null;
  }

  function hrefOf(result: IngestResult) {
    return result.kind === "innovation"
      ? resolve("/library/[[slug]]", { slug: result.slug })
      : resolve("/knowledge/[[id]]", { id: result.id });
  }

  const kindWord = (result: IngestResult) =>
    result.kind === "innovation" ? "Szkic innowacji" : "Szkic materiału";

  const size = (bytes: number) =>
    bytes > 1024 * 1024
      ? `${(bytes / 1024 / 1024).toLocaleString("pl-PL", { maximumFractionDigits: 1 })} MB`
      : `${Math.max(1, Math.round(bytes / 1024))} kB`;
</script>

<section aria-labelledby="intake-h" class="intake">
  <header class="flex items-center justify-between gap-3">
    <h2 class="font-semibold text-sm" id="intake-h">Dodaj materiał</h2>
    <button class="close" onclick={onclose} type="button">
      <span class="sr-only">Zamknij dodawanie</span>
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
        <path d="M6 6l12 12M18 6 6 18" />
      </svg>
    </button>
  </header>

  {#if job && job.status !== "running"}
    <div class="outcome" role="status">
      {#if job.status === "done" && job.result}
        <span class="added hm-land stamp-word">Dodano</span>
        <div class="grid min-w-0 gap-1">
          <span class="text-hm-ink-soft text-xs">{kindWord(job.result)}</span>
          <a class="result" href={hrefOf(job.result)}>{job.result.title}</a>
          <span class="text-hm-ink-soft text-xs"
            >Czeka na publikację: otwórz, sprawdź i&nbsp;opublikuj.</span
          >
        </div>
      {:else if job.existing}
        <div class="grid min-w-0 gap-1">
          <span class="text-hm-ink-soft text-xs"
            >Ten materiał już jest w&nbsp;bazie</span
          >
          <a class="result" href={hrefOf(job.existing)}>{job.existing.title}</a>
        </div>
      {:else}
        <div class="grid min-w-0 gap-1">
          <span class="font-semibold text-hm-bad text-sm"
            >Nie udało się dodać</span
          >
          <span class="text-sm">{job.error ?? "Nieznany błąd."}</span>
        </div>
      {/if}
      <button class="ghost cladd-clickable" onclick={again} type="button">
        <span>Dodaj kolejny</span>
      </button>
    </div>
  {:else}
    <form class="grid gap-3" novalidate onsubmit={submit}>
      <fieldset class="seg" disabled={running}>
        <legend class="sr-only">Co dodajesz</legend>
        {#each modes as m (m.id)}
          <button
            aria-pressed={mode === m.id}
            onclick={() => {
              mode = m.id;
              problem = null;
            }}
            type="button"
          >
            {m.label}
          </button>
        {/each}
      </fieldset>

      {#if mode === "url"}
        <label class="field">
          <span class="label">Adres strony lub pliku PDF</span>
          <input
            autocomplete="off"
            disabled={running}
            inputmode="url"
            placeholder="https://rops.krakow.pl/…"
            type="url"
            bind:value={url}
          >
          <span class="text-hm-ink-soft text-xs"
            >Link do innowacji z&nbsp;biblioteki ROPS doda szkic
            innowacji.</span
          >
        </label>
      {:else if mode === "pdf"}
        <input
          accept="application/pdf,.pdf"
          aria-hidden="true"
          class="sr-only"
          disabled={running}
          onchange={(event) => pick(event.currentTarget.files)}
          tabindex="-1"
          type="file"
          bind:this={fileInput}
        >
        <button
          class={["drop", dragging && "over", file && "has"]}
          disabled={running}
          onclick={() => fileInput?.click()}
          ondragleave={() => {
            dragging = false;
          }}
          ondragover={(event) => {
            event.preventDefault();
            dragging = true;
          }}
          ondrop={(event) => {
            event.preventDefault();
            dragging = false;
            pick(event.dataTransfer?.files);
          }}
          type="button"
        >
          <svg
            aria-hidden="true"
            fill="none"
            height="22"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.6"
            viewBox="0 0 24 24"
            width="22"
          >
            <path
              d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"
            />
            <path d="M14 3v5h5M12 18v-6m0 0-2.5 2.5M12 12l2.5 2.5" />
          </svg>
          {#if file}
            <span class="font-semibold text-sm">{file.name}</span>
            <span class="text-hm-ink-soft text-xs"
              >{size(file.size)}
              · kliknij, aby zmienić</span
            >
          {:else}
            <span class="font-semibold text-sm"
              >Upuść PDF albo kliknij, aby wybrać</span
            >
            <span class="text-hm-ink-soft text-xs"
              >do 30 MB, z&nbsp;warstwą tekstową</span
            >
          {/if}
        </button>
      {:else}
        <label class="field">
          <span class="label">Tekst</span>
          <textarea
            disabled={running}
            maxlength="200000"
            placeholder="Wklej treść raportu, notatki lub opisu"
            rows="6"
            bind:value={text}
          ></textarea>
          <span class="text-hm-ink-soft text-xs tabular"
            >{text.trim().length}
            znaków{text.trim().length < MIN_TEXT ? `, potrzeba co najmniej ${MIN_TEXT}` : ""}</span
          >
        </label>
      {/if}

      <label class="field">
        <span class="label"
          >Tytuł{mode === "text" ? "" : " (nieobowiązkowy)"}</span
        >
        <input disabled={running} maxlength="200" bind:value={title}>
      </label>

      {#if running && job}
        <div aria-live="polite" class="progress">
          <ol>
            {#each steps as s, i (s.id)}
              <li class={[i < stepIndex && "done", i === stepIndex && "now"]}>
                {s.label}
              </li>
            {/each}
          </ol>
          <div aria-hidden="true" class="bar">
            <i
              style:transform="scaleX({job.total ? (job.done ?? 0) / job.total : Math.max(0.04, (stepIndex + 1) / steps.length)})"
            ></i>
          </div>
        </div>
      {/if}

      <div class="flex flex-wrap items-center justify-between gap-3">
        <p class="error" role="alert">{problem ?? ""}</p>
        <button
          class="primary cladd-clickable"
          disabled={running}
          type="submit"
        >
          <span>{running ? "Dodawanie…" : "Dodaj"}</span>
        </button>
      </div>
    </form>
  {/if}
</section>

<style>
  .intake {
    display: grid;
    gap: 14px;
    padding: 18px 20px 20px;
    background: var(--hm-paper);
    border-radius: 20px;
    box-shadow: var(--hm-raised);
    animation: drop-in 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  @keyframes drop-in {
    from {
      opacity: 0;
      translate: 0 -6px;
    }
  }

  .close {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    color: var(--hm-ink-soft);
    border-radius: 9px;
  }

  .close:hover {
    color: var(--hm-ink);
    background: var(--hm-sunk);
  }

  .seg {
    display: inline-flex;
    gap: 2px;
    justify-self: start;
    padding: 3px;
    margin: 0;
    background: var(--hm-sunk);
    border: 0;
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .seg button {
    height: 30px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
    border-radius: 9px;
  }

  .seg button[aria-pressed="true"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    box-shadow: var(--shadow-cladd-outline);
  }

  .field {
    display: grid;
    gap: 6px;
  }

  .label {
    font-size: 13px;
    font-weight: 600;
  }

  input:not([type="file"]),
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
    max-height: 320px;
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

  input::placeholder,
  textarea::placeholder {
    color: var(--hm-ink-soft);
  }

  .drop {
    display: grid;
    gap: 4px;
    place-items: center;
    min-height: 120px;
    padding: 16px;
    color: var(--hm-ink-soft);
    text-align: center;
    cursor: pointer;
    background: var(--hm-sunk);
    border: 1.5px dashed
      color-mix(in oklab, var(--hm-ink-soft) 40%, transparent);
    border-radius: 14px;
    transition:
      background-color 150ms ease,
      border-color 150ms ease;
  }

  .drop span {
    color: var(--hm-ink);
  }

  .drop .text-hm-ink-soft {
    color: var(--hm-ink-soft);
  }

  .drop:hover,
  .drop.over {
    background: var(--hm-stamp-wash);
    border-color: var(--hm-stamp);
  }

  .drop:focus-within {
    outline: 2px solid var(--hm-ring);
    outline-offset: 2px;
  }

  .drop.has {
    border-style: solid;
  }

  .progress {
    display: grid;
    gap: 8px;
  }

  .progress ol {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    padding: 0;
    margin: 0;
    font-size: 12px;
    color: var(--hm-ink-soft);
    list-style: none;
  }

  .progress li.done {
    color: var(--hm-ok);
  }

  .progress li.now {
    font-weight: 650;
    color: var(--hm-stamp);
  }

  .bar {
    height: 4px;
    overflow: hidden;
    background: var(--hm-sunk);
    border-radius: 4px;
  }

  .bar i {
    display: block;
    height: 100%;
    background: var(--hm-stamp);
    transform-origin: left;
    transition: transform 500ms ease;
  }

  .error {
    min-height: 18px;
    margin: 0;
    font-size: 13px;
    font-weight: 500;
    color: var(--hm-bad);
  }

  .outcome {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    gap: 16px;
    align-items: center;
  }

  .outcome:not(:has(.added)) {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .added {
    padding: 4px 10px;
    color: var(--hm-ok);
    border: 2px solid currentColor;
    border-radius: 6px;
    rotate: -4deg;
  }

  .result {
    font-size: 15px;
    font-weight: 600;
    color: var(--hm-stamp);
    text-decoration: underline;
    text-decoration-color: color-mix(
      in oklab,
      var(--hm-stamp) 40%,
      transparent
    );
    text-underline-offset: 3px;
  }

  .primary {
    position: relative;
    display: inline-flex;
    align-items: center;
    height: 36px;
    padding: 0 18px;
    margin-left: auto;
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
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
  }

  @media (max-width: 899px) {
    .intake {
      padding: 14px;
    }

    .seg button,
    .primary,
    .ghost,
    .close {
      height: 44px;
      min-height: 44px;
    }

    .close {
      width: 44px;
    }

    .outcome,
    .outcome:not(:has(.added)) {
      grid-template-columns: minmax(0, 1fr);
      justify-items: start;
    }
  }
</style>
