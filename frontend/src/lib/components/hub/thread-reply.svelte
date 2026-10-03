<script lang="ts">
  import type { Message } from "$lib/api/admin";
  import { ApiError } from "$lib/api/client";
  import { when } from "$lib/format";
  import { showTip } from "$lib/tip";

  let {
    messages,
    canEmail,
    send,
  }: {
    messages: Message[];
    canEmail: boolean;
    send: (body: string) => Promise<Message>;
  } = $props();

  let body = $state("");
  let sending = $state(false);
  let stamp = $state<"sent" | "saved" | "failed" | null>(null);
  let field = $state<HTMLTextAreaElement | null>(null);

  const words = { failed: "Nie wysłano", saved: "Zapisano", sent: "Wysłano" };

  function delivery(m: Message): string {
    if (m.direction === "from_author") {
      return "";
    }
    const map: Record<string, string> = {
      failed: "e-mail nie dotarł",
      pending: "wysyłanie…",
      sent: "wysłano e-mailem",
      skipped: "bez e-maila, wysyłka wyłączona",
    };
    return map[m.delivery_status ?? ""] ?? "widoczne w aplikacji";
  }

  async function submit(event?: Event) {
    event?.preventDefault();
    const button = document.getElementById("send-thread-reply");
    const text = body.trim();
    if (!text || sending) {
      field?.focus();
      showTip(button, "Najpierw napisz odpowiedź", "bad");
      return;
    }
    sending = true;
    stamp = null;
    try {
      const message = await send(text);
      body = "";
      if (message.delivery_status === "failed") {
        stamp = "failed";
      } else if (message.delivery_status === "skipped") {
        stamp = "saved";
      } else {
        stamp = "sent";
      }
    } catch (e) {
      showTip(
        button,
        e instanceof ApiError ? e.message : "Brak połączenia z serwerem.",
        "bad"
      );
    } finally {
      sending = false;
    }
  }

  function keydown(event: KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      submit(event);
    }
  }
</script>

{#if messages.length > 0}
  <section aria-labelledby="thread-h">
    <h3 class="mb-1.5 font-semibold text-[13px]" id="thread-h">Rozmowa</h3>
    <ol class="thread">
      {#each messages as m (m.id)}
        <li>
          <span class="text-hm-ink-soft text-xs">
            <b class="font-semibold text-hm-ink"
              >{m.direction === "to_author" ? `ROPS${m.admin ? ` · ${m.admin.login}` : ""}` : "Autor"}</b
            >
            · {when(m.sent_at)}{delivery(m) ? ` · ${delivery(m)}` : ""}
          </span>
          <p class="whitespace-pre-line text-sm">{m.body}</p>
        </li>
      {/each}
    </ol>
  </section>
{/if}

<form class="grid gap-1.5" onsubmit={submit}>
  <h3 class="font-semibold text-[13px]">
    <label for="thread-reply">Odpowiedź do autora</label>
  </h3>
  <div class="reply">
    <textarea
      id="thread-reply"
      maxlength="5000"
      onkeydown={keydown}
      placeholder={canEmail
        ? "Wiadomość pójdzie e-mailem na adres podany przez autora."
        : "Autor nie podał e-maila. Odpowiedź zobaczy w aplikacji."}
      rows="4"
      bind:this={field}
      bind:value={body}
    ></textarea>
    <div
      class="flex items-center justify-between gap-2.5 py-1.5 pr-1.5 pl-3.5 text-hm-ink-soft text-xs"
    >
      <span class="max-[899px]:hidden"
        ><kbd>Ctrl</kbd> <kbd>Enter</kbd> wyślij</span
      >
      <span class="relative ml-auto flex items-center gap-3">
        {#if stamp}
          <span class={["sent", stamp, "hm-land stamp-word"]} role="status"
            >{words[stamp]}</span
          >
        {/if}
        <button
          class="primary cladd-clickable"
          disabled={sending}
          id="send-thread-reply"
          type="submit"
        >
          <span>{sending ? "Wysyłanie…" : "Wyślij odpowiedź"}</span>
        </button>
      </span>
    </div>
  </div>
</form>

<style>
  .thread {
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .thread li {
    display: grid;
    gap: 3px;
    padding: 10px 0;
    border-bottom: 1px solid var(--hm-rule);
  }

  .thread li:last-child {
    border-bottom: 0;
  }

  .reply {
    background: var(--hm-sunk);
    border-radius: 14px;
    box-shadow: var(--shadow-cladd-cut-outline);
  }

  .reply:focus-within {
    box-shadow:
      inset 0 0 0 1.5px var(--hm-ring),
      var(--shadow-cladd-cut-outline);
  }

  .reply textarea {
    display: block;
    width: 100%;
    min-height: 100px;
    resize: vertical;
    border: 0;
    background: none;
    outline: none;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.5;
    field-sizing: content;
  }

  .reply textarea::placeholder {
    color: var(--hm-ink-soft);
  }

  kbd {
    padding: 3px 5px;
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--hm-board);
    border-radius: 5px;
    box-shadow: var(--shadow-cladd-cut-outline);
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

  .primary:disabled {
    opacity: 0.6;
  }

  .sent {
    padding: 2px 8px;
    color: var(--hm-ok);
    border: 2px solid currentColor;
    border-radius: 6px;
    rotate: -4deg;
  }

  .sent.failed {
    color: var(--hm-bad);
  }

  .sent.saved {
    color: var(--hm-ink-soft);
  }

  @media (max-width: 899px) {
    .primary {
      height: 44px;
    }
  }
</style>
