<script lang="ts">
  import { resolve } from "$app/paths";
  import type {
    AdminFeedback,
    AdminTestSignup,
    FeedbackByInnovation,
  } from "$lib/api/admin";
  import { nbsp, plural, powiatName, when } from "$lib/format";
  import { powiats } from "$lib/live/powiats.svelte";
  import { kindLabel, signupLabel, whoLabel } from "$lib/opinions";

  let {
    slug,
    title,
    category,
    row,
    comments,
    highlight,
    signups,
    backHref,
    contactHref,
  }: {
    slug: string;
    title: string;
    category: string;
    row: FeedbackByInnovation | null;
    comments: AdminFeedback[];
    highlight: string | null;
    signups: AdminTestSignup[];
    backHref: string;
    contactHref: (email: string) => string;
  } = $props();

  const fits = $derived(row?.fits ?? 0);
  const against = $derived(row?.does_not_fit ?? 0);
  const votes = $derived(fits + against);
  const share = $derived(votes > 0 ? fits / votes : 0);
</script>

<article aria-labelledby="opinion-title" class="sheet">
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
      Opinie
    </a>
    <header class="min-w-0">
      <h2
        class="text-balance font-semibold text-[22px] tracking-tight"
        id="opinion-title"
      >
        {title || slug}
      </h2>
      <p class="mt-1.5 text-[13px] text-hm-ink-soft">
        {category ? `${category} · ` : ""}<a
          class="link"
          href={resolve("/library/[[slug]]", { slug })}
          >Otwórz w&nbsp;Bibliotece</a
        >
      </p>
    </header>

    <section aria-labelledby="tally-h" class="grid gap-2.5">
      <h3 class="sr-only" id="tally-h">Oceny</h3>
      <dl class="tally">
        <div>
          <dt>Pasuje</dt>
          <dd class="tabular">{fits}</dd>
        </div>
        <div>
          <dt>Nie pasuje</dt>
          <dd class={["tabular", against > fits && "worse"]}>{against}</dd>
        </div>
        <div>
          <dt>Uwagi</dt>
          <dd class="tabular">{row?.improvements ?? 0}</dd>
        </div>
        <div>
          <dt>Chętni do testów</dt>
          <dd class="tabular">{row?.testers ?? 0}</dd>
        </div>
      </dl>
      {#if votes > 0}
        <div class="scale">
          <span aria-hidden="true" class="rail"
            ><i style:transform="scaleX({share})"></i></span
          >
          <span class="text-hm-ink-soft text-xs tabular">
            {Math.round(share * 100)}% z&nbsp;{votes}
            {plural(votes, "oceny", "ocen", "ocen")}: pasuje
          </span>
        </div>
      {/if}
    </section>

    <section aria-labelledby="notes-h">
      <h3 class="mb-1.5 font-semibold text-[13px]" id="notes-h">
        Uwagi i&nbsp;usprawnienia
      </h3>
      {#if comments.length === 0}
        <p class="text-[13px] text-hm-ink-soft">
          Nikt nie zostawił uwag do tej innowacji.
        </p>
      {:else}
        <ol class="list">
          {#each comments as c (c.id)}
            <li
              class={[c.id === highlight && "picked"]}
              {@attach (node) => {
                if (c.id === highlight) {
                  node.scrollIntoView({ block: "nearest" });
                }
              }}
            >
              <span class="text-hm-ink-soft text-xs">
                <b class="font-semibold text-hm-ink">{kindLabel[c.kind]}</b>
                · {when(c.updated_at)}
              </span>
              <p class="text-sm text-pretty">{nbsp(c.comment ?? "")}</p>
            </li>
          {/each}
        </ol>
      {/if}
    </section>

    <section aria-labelledby="testers-h">
      <h3 class="mb-1.5 font-semibold text-[13px]" id="testers-h">
        Wolontariusze
      </h3>
      {#if signups.length === 0}
        <p class="text-[13px] text-hm-ink-soft">
          Nikt nie zgłosił się jako wolontariusz do tej innowacji.
        </p>
      {:else}
        <ol class="list">
          {#each signups as s (s.id)}
            <li>
              <a class="who" href={contactHref(s.contact_email)}>
                {s.organization || s.contact_email}
              </a>
              <span class="text-hm-ink-soft text-xs">
                {whoLabel[s.who]}{s.powiat ? ` · ${powiatName(s.powiat, powiats.names)}` : ""}
                · {when(s.created_at)}
              </span>
              {#if s.note}
                <p class="text-sm text-pretty">{nbsp(s.note)}</p>
              {/if}
              <a class="who" href={resolve("/volunteers/[[id]]", { id: s.id })}
                >{signupLabel[s.status]}
                · otwórz zgłoszenie</a
              >
            </li>
          {/each}
        </ol>
      {/if}
    </section>
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

  .link,
  .who {
    color: var(--hm-stamp);
    text-decoration: underline;
    text-decoration-color: color-mix(
      in oklab,
      var(--hm-stamp) 40%,
      transparent
    );
    text-underline-offset: 3px;
  }

  .link:hover,
  .who:hover {
    text-decoration-color: currentColor;
  }

  .who {
    justify-self: start;
    font-size: 14px;
    font-weight: 600;
  }

  .tally {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin: 0;
    border-top: 1px solid var(--hm-rule);
    border-bottom: 1px solid var(--hm-rule);
  }

  .tally div {
    display: grid;
    gap: 2px;
    padding: 10px 12px 10px 0;
  }

  .tally div + div {
    padding-left: 12px;
    border-left: 1px solid var(--hm-rule);
  }

  .tally dt {
    font-size: 12px;
    font-weight: 500;
    color: var(--hm-ink-soft);
  }

  .tally dd {
    margin: 0;
    font-size: 22px;
    font-weight: 650;
    line-height: 1.1;
    letter-spacing: -0.03em;
  }

  .tally dd.worse {
    color: var(--hm-bad);
  }

  .scale {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
    align-items: center;
  }

  .rail {
    height: 6px;
    overflow: hidden;
    background: var(--hm-tab);
    border-radius: 6px;
  }

  .rail i {
    display: block;
    height: 100%;
    background: var(--hm-stamp);
    transform-origin: left;
    transition: transform 220ms cubic-bezier(0.2, 0.8, 0.2, 1);
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

  .list li.picked {
    padding: 12px 14px;
    margin: 0 -14px;
    background: var(--hm-stamp-wash);
    border-bottom-color: transparent;
    border-radius: 12px;
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

    .tally {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .tally div:nth-child(3) {
      padding-left: 0;
      border-left: 0;
    }

    .tally div:nth-child(n + 3) {
      border-top: 1px solid var(--hm-rule);
    }

    .who {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
    }
  }
</style>
