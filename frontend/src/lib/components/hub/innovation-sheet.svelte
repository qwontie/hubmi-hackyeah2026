<script lang="ts">
  import { onDestroy, untrack } from "svelte";
  import { resolve } from "$app/paths";
  import {
    type AdminInnovation,
    type AdminInnovationDetail,
    type DemandRow,
    getInnovation,
    listDemand,
    patchInnovation,
    publishInnovation,
    type VolunteerReports,
    volunteerReports,
  } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import ErrorState from "$lib/components/error-state.svelte";
  import { plural, when } from "$lib/format";
  import { showTip } from "$lib/tip";
  import { recommendLabel } from "$lib/volunteers";

  let {
    slug,
    backHref,
    onsaved,
  }: {
    slug: string;
    backHref: string;
    onsaved: (item: AdminInnovation) => void;
  } = $props();

  type Field =
    | "title"
    | "lead"
    | "what_it_is"
    | "problems"
    | "target_group"
    | "who_can_use"
    | "effectiveness"
    | "video_url"
    | "materials_url";

  const sections: { key: Field; label: string; rows: number }[] = [
    { key: "lead", label: "W jednym zdaniu", rows: 2 },
    { key: "what_it_is", label: "Na czym polega rozwiązanie", rows: 6 },
    { key: "problems", label: "Jakich problemów dotyczy", rows: 4 },
    { key: "target_group", label: "Grupa docelowa", rows: 3 },
    { key: "who_can_use", label: "Kto może skorzystać", rows: 3 },
    { key: "effectiveness", label: "Czy to działa", rows: 4 },
  ];

  const fieldNames: Record<string, string> = {
    effectiveness: "czy to działa",
    lead: "opis w jednym zdaniu",
    materials_url: "materiały",
    problems: "problemy",
    target_group: "grupa docelowa",
    title: "tytuł",
    video_url: "film",
    what_it_is: "na czym polega",
    who_can_use: "kto może skorzystać",
  };

  let detail = $state<AdminInnovationDetail | null>(null);
  let demand = $state<DemandRow[] | null>(null);
  let reports = $state<VolunteerReports | null>(null);

  async function loadInterest(target: string) {
    const [d, r] = await Promise.all([
      listDemand({ innovation: target }).catch(() => null),
      volunteerReports(target).catch(() => null),
    ]);
    if (target === slug) {
      demand = d?.items ?? null;
      reports = r;
    }
  }

  const demandTotal = $derived(
    (demand ?? []).reduce((sum, row) => sum + row.count, 0)
  );
  let draft = $state<Record<Field, string>>(blank());
  let loadError = $state<Error | null>(null);
  let saving = $state(false);
  let controller: AbortController | null = null;

  function blank(): Record<Field, string> {
    return {
      effectiveness: "",
      lead: "",
      materials_url: "",
      problems: "",
      target_group: "",
      title: "",
      video_url: "",
      what_it_is: "",
      who_can_use: "",
    };
  }

  function fill(item: AdminInnovationDetail) {
    detail = item;
    const next = blank();
    for (const key of Object.keys(next) as Field[]) {
      next[key] = item[key] ?? "";
    }
    draft = next;
  }

  const changed = $derived.by(() => {
    if (!detail) {
      return [] as Field[];
    }
    const current = detail;
    return (Object.keys(draft) as Field[]).filter(
      (key) => draft[key].trim() !== (current[key] ?? "").trim()
    );
  });

  const saveLabel = $derived.by(() => {
    if (saving) {
      return "Zapisywanie…";
    }
    return changed.length > 0 ? `Zapisz zmiany (${changed.length})` : "Zapisz";
  });

  async function load(target: string) {
    controller?.abort();
    controller = new AbortController();
    loadError = null;
    try {
      const item = await getInnovation(target, controller.signal);
      if (target === slug) {
        fill(item);
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        return;
      }
      loadError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    const target = slug;
    untrack(() => {
      detail = null;
      demand = null;
      reports = null;
      load(target);
      loadInterest(target);
    });
  });

  onDestroy(() => controller?.abort());

  async function save(event: SubmitEvent) {
    event.preventDefault();
    const button = document.getElementById("save-innovation");
    if (!detail || changed.length === 0 || saving) {
      showTip(button, "Nic się nie zmieniło");
      return;
    }
    saving = true;
    const body: Record<string, string | null> = {};
    for (const key of changed) {
      const value = draft[key].trim();
      body[key] = value === "" && key !== "title" ? null : value;
    }
    try {
      const item = await patchInnovation(
        detail.slug,
        body as Partial<AdminInnovationDetail>
      );
      fill(item);
      onsaved(item);
      showTip(button, "Zapisano");
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

  async function togglePublish(event: MouseEvent) {
    if (!detail) {
      return;
    }
    const button = event.currentTarget as HTMLElement;
    const publish = detail.status !== "published";
    try {
      const item = await publishInnovation(detail.slug, publish);
      fill(item);
      onsaved(item);
      showTip(button, publish ? "Opublikowano" : "Ukryto");
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Nie udało się.",
        "bad"
      );
    }
  }

  function keydown(event: KeyboardEvent) {
    if (event.key === "s" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      (
        document.getElementById("innovation-form") as HTMLFormElement | null
      )?.requestSubmit();
    }
  }
</script>

<svelte:window onkeydown={keydown} />

<article aria-labelledby="innovation-title" class="sheet">
  {#if detail}
    <form class="grid max-w-[680px] gap-5" id="innovation-form" onsubmit={save}>
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
        Biblioteka
      </a>
      <header class="grid gap-1.5">
        <label class="sr-only" for="f-title">Tytuł</label>
        <textarea
          class="title"
          id="f-title"
          maxlength="200"
          required
          rows="1"
          bind:value={draft.title}
        ></textarea>
        <p class="text-[13px] text-hm-ink-soft" id="innovation-title">
          {detail.category.name}
          ·
          {detail.status === "published" ? "opublikowana" : "szkic, niewidoczna dla mieszkańców"}
          {#if detail.source_url}
            ·
            <a
              class="link"
              href={detail.source_url}
              rel="noopener"
              target="_blank"
              >strona ROPS</a
            >
          {/if}
        </p>
        {#if detail.edited_fields.length > 0}
          <p class="text-[13px] text-hm-ink-soft">
            Zmienione ręcznie{detail.edited_at ? ` ${when(detail.edited_at)}` : ""}:
            {detail.edited_fields.map((f) => fieldNames[f] ?? f).join(", ")}.
            Import z&nbsp;ROPS tego nie nadpisze.
          </p>
        {/if}
      </header>

      {#each sections as section (section.key)}
        <div class="grid gap-1.5">
          <label class="font-semibold text-[13px]" for="f-{section.key}"
            >{section.label}</label
          >
          <textarea
            class="well"
            id="f-{section.key}"
            rows={section.rows}
            bind:value={draft[section.key]}
          ></textarea>
        </div>
      {/each}

      <div class="grid gap-3 min-[900px]:grid-cols-2">
        <div class="grid gap-1.5">
          <label class="font-semibold text-[13px]" for="f-video_url"
            >Film (adres)</label
          >
          <input
            class="well h-10"
            id="f-video_url"
            inputmode="url"
            type="url"
            bind:value={draft.video_url}
          >
        </div>
        <div class="grid gap-1.5">
          <label class="font-semibold text-[13px]" for="f-materials_url"
            >Materiały do pobrania (adres)</label
          >
          <input
            class="well h-10"
            id="f-materials_url"
            inputmode="url"
            type="url"
            bind:value={draft.materials_url}
          >
        </div>
      </div>

      {#if detail.authors.length > 0}
        <p class="text-[13px] text-hm-ink-soft">
          Autorzy: {detail.authors.join(", ")}
        </p>
      {/if}

      <section aria-labelledby="interest-h" class="interest">
        <h3 class="font-semibold text-[13px]" id="interest-h">
          Zainteresowanie mieszkańców
          <span class="font-normal text-hm-ink-soft">od początku</span>
        </h3>
        {#if demand === null && reports === null}
          <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
        {:else}
          <p class="text-sm">
            <b class="font-semibold">"Chcę tego u&nbsp;siebie"</b>:
            {demandTotal}
            {plural(demandTotal, "zgłoszenie", "zgłoszenia", "zgłoszeń")}{demand && demand.length > 0 ? ` · ${demand.map((d) => `${d.powiat_name} ${d.count}`).join(", ")}` : ""}
          </p>
          {#if reports}
            <p class="text-sm">
              <b class="font-semibold">Wolontariusze</b>:
              {reports.items.length}
              {plural(reports.items.length, "zgłoszenie", "zgłoszenia", "zgłoszeń")},
              {reports.reports}
              {plural(reports.reports, "raport", "raporty", "raportów")}{reports.reports > 0 ? `, ${reports.participants} ${plural(reports.participants, "uczestnik", "uczestników", "uczestników")}; poleca: tak ${reports.recommend.yes}, po zmianach ${reports.recommend.after_changes}, nie ${reports.recommend.no}` : ""}
              ·
              <a
                class="link"
                href="{resolve('/volunteers/[[id]]', {})}?innovation={slug}"
                >otwórz zgłoszenia</a
              >
            </p>
            {#each reports.items.filter((v) => v.report) as v (v.id)}
              <p class="text-[13px] text-hm-ink-soft">
                <a
                  class="link"
                  href={resolve("/volunteers/[[id]]", { id: v.id })}
                  >{v.organization || v.email}</a
                >, {v.powiat_name}:
                {v.report ? recommendLabel[v.report.recommend] : ""}{v.report?.worked ? ` · ${v.report.worked}` : ""}
              </p>
            {/each}
          {/if}
        {/if}
      </section>

      <div class="foot">
        <button
          class="ghost cladd-clickable"
          onclick={togglePublish}
          type="button"
        >
          <span
            >{detail.status === "published" ? "Ukryj przed mieszkańcami" : "Opublikuj"}</span
          >
        </button>
        <span class="flex items-center gap-3">
          <span class="text-hm-ink-soft text-xs max-[899px]:hidden"
            ><kbd>Ctrl</kbd> <kbd>S</kbd></span
          >
          <button
            class="primary cladd-clickable"
            disabled={saving}
            id="save-innovation"
            type="submit"
          >
            <span>{saveLabel}</span>
          </button>
        </span>
      </div>
    </form>
  {:else if loadError}
    <ErrorState error={loadError} retry={() => load(slug)} />
  {:else}
    <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
  {/if}
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
    border-radius: 8px;
  }

  .title:focus-visible {
    border-radius: 0;
    box-shadow: 0 2px 0 var(--hm-ring);
  }

  .link {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-underline-offset: 3px;
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

  .interest {
    display: grid;
    gap: 6px;
    padding: 12px 14px;
    background: var(--hm-sunk);
    border-radius: 12px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .foot {
    position: sticky;
    bottom: 0;
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
    padding: 14px 0 20px;
    background: linear-gradient(to top, var(--hm-paper) 75%, transparent);
  }

  kbd {
    padding: 3px 5px;
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--hm-board);
    border-radius: 5px;
    box-shadow: var(--shadow-cladd-cut-outline);
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

  .primary:disabled {
    opacity: 0.6;
  }

  .ghost {
    color: var(--hm-ink);
    background: var(--hm-sunk);
    box-shadow: var(--shadow-cladd-outline);
  }

  .ghost:hover {
    background: var(--hm-stamp-wash);
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
      padding: 0 10px 0 4px;
      font-size: 14px;
      font-weight: 500;
    }

    .primary,
    .ghost {
      height: 44px;
    }
  }
</style>
