<script lang="ts">
  import { resolve } from "$app/paths";
  import {
    type AdminFeedback,
    type AdminNeed,
    type AdminTestSignup,
    listAllNeeds,
    type SignupStatus,
  } from "$lib/api/admin";
  import ErrorState from "$lib/components/error-state.svelte";
  import SignupStatusControl from "$lib/components/hub/signup-status.svelte";
  import {
    dayWords,
    nbsp,
    powiatName,
    registerNumber,
    statusLabel,
    when,
  } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { contactKey, kindLabel, whoLabel } from "$lib/opinions";
  import { showTip } from "$lib/tip";

  let {
    email,
    signups,
    feedback,
    backHref,
    innovationHref,
    onstatus,
  }: {
    email: string;
    signups: AdminTestSignup[];
    feedback: AdminFeedback[];
    backHref: string;
    innovationHref: (slug: string) => string;
    onstatus: (
      signup: AdminTestSignup,
      status: SignupStatus,
      anchor: HTMLElement | null
    ) => void;
  } = $props();

  let allNeeds = $state<AdminNeed[] | null>(null);
  let needsError = $state<Error | null>(null);

  async function loadNeeds() {
    needsError = null;
    try {
      allNeeds = await listAllNeeds();
    } catch (e) {
      needsError = e instanceof Error ? e : new Error(String(e));
    }
  }

  $effect(() => {
    loadNeeds();
  });

  const address = $derived(signups[0]?.contact_email ?? email);
  const needs = $derived(
    (allNeeds ?? []).filter(
      (n) => n.contact_email && contactKey(n.contact_email) === email
    )
  );
  const needIds = $derived(new Set(needs.map((n) => n.id)));
  const ratings = $derived(
    feedback.filter((f) => f.need_id && needIds.has(f.need_id))
  );
  const organizations = $derived([
    ...new Set(signups.map((s) => s.organization).filter(Boolean)),
  ]);
  const roles = $derived([...new Set(signups.map((s) => whoLabel[s.who]))]);
  const places = $derived([
    ...new Set(
      [...signups.map((s) => s.powiat), ...needs.map((n) => n.powiat)]
        .filter((p): p is string => Boolean(p))
        .map((p) => powiatName(p, powiats.names))
    ),
  ]);
  const first = $derived(
    [...signups.map((s) => s.created_at), ...needs.map((n) => n.created_at)]
      .sort()
      .at(0) ?? null
  );
  const meta = $derived(
    [
      organizations.length > 0 ? address : "",
      ...roles,
      ...places,
      first ? `od ${dayWords(first)}` : "",
    ].filter(Boolean)
  );

  function copy(event: MouseEvent) {
    const anchor = event.currentTarget as HTMLElement;
    navigator.clipboard
      .writeText(address)
      .then(() => showTip(anchor, "Skopiowano adres"))
      .catch(() => showTip(anchor, "Nie udało się skopiować.", "bad"));
  }
</script>

<article aria-labelledby="contact-title" class="sheet">
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
      Zgłoszenia
    </a>
    <header class="grid gap-3">
      <div class="min-w-0">
        <h2
          class="break-words font-semibold text-[22px] tracking-tight"
          id="contact-title"
        >
          {organizations.join(", ") || address}
        </h2>
        <p class="mt-1.5 text-[13px] text-hm-ink-soft">{meta.join(" · ")}</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <a class="primary cladd-clickable" href="mailto:{address}">
          <span class="flex items-center gap-2">
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
              <rect height="14" rx="2.5" width="18" x="3" y="5" />
              <path d="m4 7 8 6 8-6" />
            </svg>
            Napisz e-mail
          </span>
        </a>
        <button class="ghost cladd-clickable" onclick={copy} type="button">
          <span>Kopiuj adres</span>
        </button>
      </div>
    </header>

    <section aria-labelledby="c-signups-h">
      <h3 class="mb-1.5 font-semibold text-[13px]" id="c-signups-h">
        Zgłoszenia do testów
        <span class="font-medium text-hm-ink-soft tabular"
          >{signups.length}</span
        >
      </h3>
      {#if signups.length === 0}
        <p class="text-[13px] text-hm-ink-soft">
          Z tego adresu nikt nie zgłosił się do testów.
        </p>
      {:else}
        <ol class="list">
          {#each signups as s (s.id)}
            <li>
              <a class="title" href={innovationHref(s.innovation.slug)}
                >{s.innovation.title}</a
              >
              <span class="text-hm-ink-soft text-xs">
                {whoLabel[s.who]}{s.powiat ? ` · ${powiatName(s.powiat, powiats.names)}` : ""}
                · {when(s.created_at)}
              </span>
              {#if s.note}
                <p class="text-sm text-pretty">{nbsp(s.note)}</p>
              {/if}
              <SignupStatusControl {onstatus} signup={s} />
            </li>
          {/each}
        </ol>
      {/if}
    </section>

    <section aria-labelledby="c-needs-h">
      <h3 class="mb-1.5 font-semibold text-[13px]" id="c-needs-h">
        Potrzeby z&nbsp;tego adresu
        {#if allNeeds}
          <span class="font-medium text-hm-ink-soft tabular"
            >{needs.length}</span
          >
        {/if}
      </h3>
      {#if needsError}
        <ErrorState class="py-2" error={needsError} retry={loadNeeds} />
      {:else if allNeeds === null}
        <p class="text-[13px] text-hm-ink-soft">Wczytywanie…</p>
      {:else if needs.length === 0}
        <p class="text-[13px] text-hm-ink-soft">
          Z tego adresu nie zgłoszono żadnej potrzeby.
        </p>
      {:else}
        <ol class="list">
          {#each needs as n (n.id)}
            <li>
              <a class="title" href={resolve("/needs/[[id]]", { id: n.id })}>
                Potrzeba
                {n.number ? `nr ${registerNumber(n.number)}` : ""}
              </a>
              <span class="text-hm-ink-soft text-xs"
                >{statusLabel[n.status]}
                · {when(n.created_at)}</span
              >
              <p class="clamp text-sm">{nbsp(n.text)}</p>
            </li>
          {/each}
        </ol>
      {/if}
    </section>

    {#if ratings.length > 0}
      <section aria-labelledby="c-votes-h">
        <h3 class="mb-1.5 font-semibold text-[13px]" id="c-votes-h">
          Oceny dopasowanych rozwiązań
          <span class="font-medium text-hm-ink-soft tabular"
            >{ratings.length}</span
          >
        </h3>
        <ol class="list">
          {#each ratings as f (f.id)}
            <li>
              <span class="text-sm">
                <b class="font-semibold">{kindLabel[f.kind]}</b>
                ·
                <a class="title" href={innovationHref(f.innovation.slug)}
                  >{f.innovation.title}</a
                >
              </span>
              {#if f.comment}
                <p class="text-sm text-pretty">{nbsp(f.comment)}</p>
              {/if}
              <span class="text-hm-ink-soft text-xs">{when(f.updated_at)}</span>
            </li>
          {/each}
        </ol>
      </section>
    {/if}
  </div>
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

  .title {
    justify-self: start;
    font-size: 14px;
    font-weight: 600;
    text-decoration: underline;
    text-decoration-color: var(--hm-rule);
    text-underline-offset: 3px;
  }

  .title:hover {
    color: var(--hm-stamp);
    text-decoration-color: currentColor;
  }

  .clamp {
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    -webkit-line-clamp: 3;
    line-clamp: 3;
  }

  .list {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .list li {
    display: grid;
    gap: 6px;
    padding: 12px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .list li:last-child {
    border-bottom: 0;
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

    .title {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
    }
  }
</style>
