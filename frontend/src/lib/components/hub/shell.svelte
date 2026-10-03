<script lang="ts">
  import type { Snippet } from "svelte";
  import { goto } from "$app/navigation";
  import { asset, resolve } from "$app/paths";
  import { page } from "$app/state";
  import { logout } from "$lib/api/auth";
  import { api } from "$lib/api/client";
  import { session } from "$lib/auth/session.svelte";
  import RopsColophon from "$lib/components/hub/rops-colophon.svelte";
  import { inbox } from "$lib/live/inbox.svelte";
  import { powiats } from "$lib/live/powiats.svelte";
  import { live } from "$lib/live/stream.svelte";

  let { children }: { children: Snippet } = $props();

  const expert = $derived(session.me?.role === "expert");
  const expertPath = resolve("/expert");
  const onExpert = $derived(page.url.pathname.startsWith(expertPath));

  let demo = $state(false);

  $effect(() => {
    api
      .get<{ demo: boolean }>("/meta")
      .then(({ demo: loaded }) => {
        demo = loaded;
      })
      .catch(() => {
        demo = false;
      });
  });

  $effect(() => {
    powiats.load();
    if (!expert) {
      inbox.start();
    }
  });

  $effect(() => {
    if (expert && !onExpert) {
      goto(expertPath, { replaceState: true });
    }
  });

  const needsPath = resolve("/needs");
  const libraryPath = resolve("/library");
  const onNeeds = $derived(page.url.pathname.startsWith(needsPath));
  const onLibrary = $derived(page.url.pathname.startsWith(libraryPath));
  const statsPath = resolve("/stats");
  const onStats = $derived(page.url.pathname.startsWith(statsPath));
  const ideasPath = resolve("/ideas");
  const onIdeas = $derived(page.url.pathname.startsWith(ideasPath));
  const grantsPath = resolve("/grants/[[id]]", {});
  const onGrants = $derived(
    Boolean(
      page.route.id?.startsWith("/grants") ||
        page.route.id?.startsWith("/applications")
    )
  );
  const opinionsPath = resolve("/opinions");
  const onOpinions = $derived(page.url.pathname.startsWith(opinionsPath));
  const knowledgePath = resolve("/knowledge");
  const onKnowledge = $derived(page.url.pathname.startsWith(knowledgePath));

  const liveWords: Record<string, string> = {
    connecting: "Łączenie…",
    offline: "Brak połączenia",
    open: "Na żywo",
  };
  const liveDots: Record<string, string> = {
    connecting: "bg-hm-warn",
    offline: "bg-hm-bad",
    open: "bg-hm-live",
  };

  function skip(event: MouseEvent) {
    const main = document.querySelector<HTMLElement>("main");
    if (!main) {
      return;
    }
    event.preventDefault();
    main.setAttribute("tabindex", "-1");
    main.focus();
  }

  async function signOut() {
    try {
      await logout();
    } finally {
      live.stop();
      session.set(null);
      await goto(resolve("/login"), { replaceState: true });
    }
  }
</script>

<div
  class="grid h-dvh grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)_auto] bg-hm-desk text-hm-ink max-[899px]:h-auto max-[899px]:min-h-dvh"
>
  <a class="skip" href="#main" onclick={skip}>Przejdź do treści</a>
  <header
    class="flex flex-wrap items-center gap-x-7 gap-y-2.5 px-3 py-2.5 min-[900px]:h-15 min-[900px]:px-5 min-[900px]:py-0"
  >
    <a
      class="flex items-center gap-2 rounded-xl"
      href={expert ? expertPath : needsPath}
    >
      <img
        alt=""
        class="signet"
        height="63"
        src={asset("/brand/rops-signet.svg")}
        width="82"
      >
      <span class="leading-tight">
        <b class="block font-semibold text-[15px] tracking-tight">HubMi</b>
        <span class="text-hm-ink-soft text-xs">ROPS Kraków</span>
        {#if demo}
          <span class="block text-hm-ink-soft text-xs min-[900px]:hidden"
            >Dane pokazowe</span
          >
        {/if}
      </span>
    </a>
    <nav
      aria-label="Główne"
      class="nav order-3 w-full min-w-0 overflow-x-auto min-[900px]:order-none min-[900px]:w-auto"
    >
      {#if expert}
        <a aria-current={onExpert ? "page" : undefined} href={expertPath}
          >Moje zadania</a
        >
      {:else}
        <a aria-current={onNeeds ? "page" : undefined} href={needsPath}>
          Dziennik potrzeb
          {#if inbox.newCount > 0}
            <span class="font-semibold text-hm-stamp text-xs tabular"
              >{inbox.newCount}<span class="sr-only"> nowych</span></span
            >
          {/if}
        </a>
        <a aria-current={onLibrary ? "page" : undefined} href={libraryPath}
          >Biblioteka</a
        >
        <a aria-current={onKnowledge ? "page" : undefined} href={knowledgePath}
          >Wiedza</a
        >
        <a aria-current={onIdeas ? "page" : undefined} href={ideasPath}
          >Pomysły</a
        >
        <a aria-current={onGrants ? "page" : undefined} href={grantsPath}
          >Nabory</a
        >
        <a aria-current={onOpinions ? "page" : undefined} href={opinionsPath}
          >Opinie i&nbsp;zgłoszenia</a
        >
        <a aria-current={onStats ? "page" : undefined} href={statsPath}
          >Statystyki</a
        >
      {/if}
    </nav>
    <div class="ml-auto flex items-center gap-4 text-[13px] text-hm-ink-soft">
      {#if demo}
        <span class="demo max-[899px]:hidden">W bazie są dane pokazowe</span>
      {/if}
      {#if !expert}
        <span class="flex items-center gap-2" role="status">
          <i class={["size-[7px] rounded-full", liveDots[live.state]]}></i>
          <span>{liveWords[live.state]}</span>
        </span>
      {/if}
      <button class="signout" onclick={signOut} type="button">
        <span class="max-[899px]:sr-only"
          >{session.me?.display_name ?? session.me?.login}</span
        >
        <span class="sr-only">, wyloguj się</span>
        <span aria-hidden="true" class="text-hm-ink-soft">Wyloguj</span>
      </button>
    </div>
  </header>
  {@render children()}
  <RopsColophon />
</div>

<style>
  .signet {
    width: auto;
    height: 30px;
  }

  .nav {
    display: flex;
    gap: 2px;
    padding: 3px;
    background: color-mix(in oklab, var(--hm-ink) 6%, transparent);
    border-radius: 13px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .nav a {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    height: 34px;
    padding: 0 12px;
    font-size: 13px;
    font-weight: 500;
    color: var(--hm-ink-soft);
    white-space: nowrap;
    border-radius: 10px;
    transition: background-color 150ms ease;
  }

  .nav a:hover {
    background: color-mix(in oklab, var(--hm-paper) 50%, transparent);
  }

  .nav a[aria-current="page"] {
    color: var(--hm-ink);
    background: var(--hm-paper);
    background-image: linear-gradient(
      to bottom right,
      oklch(1 0 0 / 0.6),
      transparent
    );
    box-shadow: var(--shadow-cladd-outline);
  }

  .skip {
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 80;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 600;
    color: var(--hm-on-stamp);
    background: var(--hm-stamp);
    border-radius: 10px;
    translate: 0 -200%;
  }

  .skip:focus-visible {
    translate: 0 0;
  }

  .demo {
    font-size: 12px;
    white-space: nowrap;
  }

  .signout {
    display: inline-flex;
    gap: 8px;
    align-items: center;
    min-height: 34px;
    padding: 0 10px;
    color: var(--hm-ink);
    border-radius: 10px;
    transition: background-color 150ms ease;
  }

  .signout:hover {
    background: color-mix(in oklab, var(--hm-paper) 60%, transparent);
  }

  @media (max-width: 899px) {
    .nav {
      scrollbar-width: none;
      mask-image: linear-gradient(
        to right,
        black calc(100% - 28px),
        transparent
      );
    }

    .nav a:last-child {
      margin-right: 24px;
    }
  }

  @media (max-width: 899px), (pointer: coarse) {
    .nav a,
    .signout {
      height: 44px;
      min-height: 44px;
    }
  }
</style>
