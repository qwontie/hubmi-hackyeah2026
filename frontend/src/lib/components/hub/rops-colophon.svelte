<script lang="ts">
  import { asset } from "$app/paths";

  let { variant = "bar" }: { variant?: "bar" | "stack" } = $props();

  const links = [
    { href: "https://rops.krakow.pl/", label: "rops.krakow.pl" },
    {
      href: "https://rops.krakow.pl/innowacje-spoleczne/biblioteka-innowacji-spolecznych/kategorie",
      label: "Biblioteka innowacji ROPS",
    },
    {
      href: "https://rops.krakow.pl/kontakt/regionalny-osrodek-polityki-spolecznej-w-krakowie",
      label: "Kontakt",
    },
    {
      href: "https://rops.krakow.pl/polityka-prywatnosci",
      label: "Polityka prywatności",
    },
  ];
</script>

<footer class={["colophon", variant]}>
  <div class="marks">
    <a
      class="mark"
      href="https://rops.krakow.pl/"
      rel="noreferrer"
      target="_blank"
    >
      <img
        alt="Regionalny Ośrodek Polityki Społecznej w Krakowie, instytucja Województwa Małopolskiego"
        class="rops"
        height="72"
        src={asset("/brand/rops.svg")}
        width="230"
      >
      <span class="sr-only">(otwiera się w nowej karcie)</span>
    </a>
    <i aria-hidden="true" class="rule"></i>
    <a
      class="mark"
      href="https://www.malopolska.pl/"
      rel="noreferrer"
      target="_blank"
    >
      <img
        alt="Województwo Małopolskie"
        class="mp"
        height="55"
        src={asset("/brand/malopolska.svg")}
        width="401"
      >
      <span class="sr-only">(otwiera się w nowej karcie)</span>
    </a>
  </div>
  <nav aria-label="Strony ROPS" class="links">
    {#each links as l (l.href)}
      <a href={l.href} rel="noreferrer" target="_blank"
        >{l.label}<span class="sr-only"> (otwiera się w nowej karcie)</span></a
      >
    {/each}
  </nav>
</footer>

<style>
  .colophon {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 20px;
    align-items: center;
    justify-content: space-between;
    font-size: 12px;
    color: var(--hm-ink-soft);
  }

  .bar {
    min-height: 48px;
    padding: 0 22px 8px 24px;
  }

  .stack {
    flex-direction: column;
    gap: 14px;
    justify-content: center;
    margin-top: 24px;
  }

  .marks {
    display: flex;
    gap: 14px;
    align-items: center;
  }

  .mark {
    display: inline-flex;
    align-items: center;
    min-height: 32px;
    border-radius: 6px;
    opacity: 0.88;
    transition: opacity 150ms ease;
  }

  .mark:hover {
    opacity: 1;
  }

  .rops {
    width: auto;
    height: 34px;
  }

  .mp {
    width: auto;
    height: 12px;
  }

  .stack .rops {
    height: 40px;
  }

  .stack .mp {
    height: 15px;
  }

  .rule {
    width: 1px;
    height: 20px;
    background: var(--hm-rule);
  }

  .links {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 16px;
  }

  .stack .links {
    justify-content: center;
  }

  .links a {
    display: inline-flex;
    align-items: center;
    min-height: 32px;
    text-decoration: underline;
    text-decoration-color: transparent;
    text-underline-offset: 3px;
    border-radius: 6px;
    transition:
      color 150ms ease,
      text-decoration-color 150ms ease;
  }

  .links a:hover {
    color: var(--hm-ink);
    text-decoration-color: currentColor;
  }

  @media (max-width: 899px) {
    .bar {
      flex-direction: column;
      align-items: flex-start;
      padding: 12px 14px 18px;
    }

    .mark,
    .links a {
      min-height: 44px;
    }
  }
</style>
