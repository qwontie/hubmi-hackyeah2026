from dataclasses import dataclass
from enum import StrEnum
from html import escape

from .sender import Email

SIGNATURE = (
    "Zespół Małopolskiego Centrum Innowacji Społecznych\n"
    "Regionalny Ośrodek Polityki Społecznej w Krakowie"
)
EXCERPT_LENGTH = 280
DIGEST_LIMIT = 20
CONSENT_NOTE = (
    "Ta wiadomość trafia do Ciebie, bo przy zgłoszeniu podano ten adres "
    "i wyrażono zgodę na kontakt."
)
H1 = '<h1 style="font-size:22px;margin:0 0 16px">'


class StaffItemKind(StrEnum):
    NOTHING_FITS = "nothing_fits"
    FORM_NEED = "form_need"
    IDEA = "idea"
    AUTHOR_MESSAGE = "author_message"
    IDEA_MESSAGE = "idea_message"


STAFF_ITEM_LABELS = {
    StaffItemKind.NOTHING_FITS: "Zgłoszenie bez pasującej innowacji",
    StaffItemKind.FORM_NEED: "Nowe zgłoszenie potrzeby z formularza",
    StaffItemKind.IDEA: "Nowy pomysł",
    StaffItemKind.AUTHOR_MESSAGE: "Nowa wiadomość od autora zgłoszenia",
    StaffItemKind.IDEA_MESSAGE: "Nowa wiadomość od autora pomysłu",
}


@dataclass(frozen=True, slots=True)
class StaffItem:
    kind: StaffItemKind
    key: str
    text: str
    url: str


def excerpt(text: str, limit: int = EXCERPT_LENGTH) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


def plural(count: int, one: str, few: str, many: str) -> str:
    if count == 1:
        return one
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return few
    return many


def html_paragraphs(text: str) -> str:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    return "".join(
        f'<p style="margin:0 0 16px">{escape(block).replace(chr(10), "<br>")}</p>'
        for block in blocks
    )


def html_document(title: str, content: str) -> str:
    return (
        '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        f"<title>{escape(title)}</title></head>"
        '<body style="margin:0;padding:24px;background:#f5f5f4;color:#1c1917;'
        'font-family:Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5">'
        '<main style="max-width:600px;margin:0 auto;background:#ffffff;'
        'padding:32px;border-radius:12px">'
        f"{content}</main></body></html>"
    )


def html_button(url: str, label: str) -> str:
    return (
        f'<p style="margin:24px 0"><a href="{escape(url)}" style="display:inline-block;'
        "background:#1c1917;color:#ffffff;padding:12px 20px;border-radius:8px;"
        f'text-decoration:none;font-weight:bold">{escape(label)}</a></p>'
    )


def html_quote(text: str) -> str:
    return (
        '<blockquote style="margin:0 0 16px;padding:12px 16px;'
        "border-left:4px solid #a8a29e;"
        f'background:#fafaf9;color:#44403c">{escape(text)}</blockquote>'
    )


def author_reply(
    *, to: str, need_text: str, body: str, thread_url: str, idempotency_key: str
) -> Email:
    subject = "Odpowiedź ROPS na Twoje zgłoszenie w HubMi"
    quote = excerpt(need_text)
    text = (
        "Dzień dobry,\n\n"
        "Regionalny Ośrodek Polityki Społecznej w Krakowie odpowiedział na zgłoszenie "
        "przesłane przez HubMi.\n\n"
        f"Zgłoszenie:\n„{quote}”\n\n"
        f"Odpowiedź:\n{body}\n\n"
        f"Całą rozmowę zobaczysz i odpowiesz na nią tutaj:\n{thread_url}\n\n"
        f"{SIGNATURE}\n\n"
        f"{CONSENT_NOTE}"
    )
    html = html_document(
        subject,
        f"{H1}Odpowiedź na Twoje zgłoszenie</h1>"
        '<p style="margin:0 0 16px">Regionalny Ośrodek Polityki Społecznej w Krakowie '
        "odpowiedział na zgłoszenie przesłane przez HubMi.</p>"
        '<h2 style="font-size:16px;margin:0 0 8px">Zgłoszenie</h2>'
        f"{html_quote(quote)}"
        '<h2 style="font-size:16px;margin:0 0 8px">Odpowiedź</h2>'
        f"{html_paragraphs(body)}"
        f"{html_button(thread_url, 'Zobacz rozmowę i odpowiedz')}"
        f"{html_paragraphs(SIGNATURE)}"
        '<p style="margin:24px 0 0;font-size:13px;color:#57534e">'
        f"{CONSENT_NOTE}</p>",
    )
    return Email(
        to=to, subject=subject, text=text, html=html, idempotency_key=idempotency_key
    )


def idea_reply(
    *, to: str, idea_title: str, body: str, thread_url: str, idempotency_key: str
) -> Email:
    subject = "Odpowiedź ROPS na Twój pomysł w HubMi"
    title = excerpt(idea_title, 200)
    text = (
        "Dzień dobry,\n\n"
        "Regionalny Ośrodek Polityki Społecznej w Krakowie odpowiedział na pomysł "
        "przesłany przez HubMi.\n\n"
        f"Pomysł:\n„{title}”\n\n"
        f"Odpowiedź:\n{body}\n\n"
        f"Całą rozmowę zobaczysz i odpowiesz na nią tutaj:\n{thread_url}\n\n"
        f"{SIGNATURE}\n\n"
        f"{CONSENT_NOTE}"
    )
    html = html_document(
        subject,
        f"{H1}Odpowiedź na Twój pomysł</h1>"
        '<p style="margin:0 0 16px">Regionalny Ośrodek Polityki Społecznej w Krakowie '
        "odpowiedział na pomysł przesłany przez HubMi.</p>"
        '<h2 style="font-size:16px;margin:0 0 8px">Pomysł</h2>'
        f"{html_quote(title)}"
        '<h2 style="font-size:16px;margin:0 0 8px">Odpowiedź</h2>'
        f"{html_paragraphs(body)}"
        f"{html_button(thread_url, 'Zobacz rozmowę i odpowiedz')}"
        f"{html_paragraphs(SIGNATURE)}"
        '<p style="margin:24px 0 0;font-size:13px;color:#57534e">'
        f"{CONSENT_NOTE}</p>",
    )
    return Email(
        to=to, subject=subject, text=text, html=html, idempotency_key=idempotency_key
    )


def staff_digest(*, to: str, items: list[StaffItem], inbox_url: str) -> Email:
    count = len(items)
    noun = plural(count, "nowa sprawa", "nowe sprawy", "nowych spraw")
    subject = f"HubMi: {count} {noun} do przejrzenia"
    shown = items[:DIGEST_LIMIT]
    hidden = count - len(shown)
    lines = [
        f"- {STAFF_ITEM_LABELS[item.kind]}: „{excerpt(item.text, 200)}”\n  {item.url}"
        for item in shown
    ]
    if hidden:
        lines.append(f"- i {hidden} więcej w skrzynce")
    text = (
        "Dzień dobry,\n\n"
        "W HubMi pojawiły się sprawy, które czekają na zespół ROPS:\n\n"
        + "\n".join(lines)
        + f"\n\nSkrzynka zgłoszeń: {inbox_url}\n"
    )
    rows = "".join(
        '<li style="margin:0 0 16px">'
        f"<strong>{escape(STAFF_ITEM_LABELS[item.kind])}</strong><br>"
        f"„{escape(excerpt(item.text, 200))}”<br>"
        f'<a href="{escape(item.url)}" style="color:#1d4ed8">Otwórz w panelu</a></li>'
        for item in shown
    )
    if hidden:
        rows += f'<li style="margin:0 0 16px">i {hidden} więcej w skrzynce</li>'
    html = html_document(
        subject,
        f"{H1}{escape(subject)}</h1>"
        '<p style="margin:0 0 16px">W HubMi pojawiły się sprawy, '
        "które czekają na zespół ROPS.</p>"
        f'<ul style="padding-left:20px;margin:0 0 16px">{rows}</ul>'
        f"{html_button(inbox_url, 'Otwórz skrzynkę zgłoszeń')}",
    )
    return Email(to=to, subject=subject, text=text, html=html)


def expert_message(  # noqa: PLR0913
    *,
    to: str,
    about: str,
    is_idea: bool,
    expert_name: str,
    expertise: str | None,
    body: str,
    thread_url: str,
    idempotency_key: str,
) -> Email:
    label = "Pomysł" if is_idea else "Zgłoszenie"
    subject = (
        "Opinia eksperta o Twoim pomyśle w HubMi"
        if is_idea
        else "Opinia eksperta o Twoim zgłoszeniu w HubMi"
    )
    who = f"{expert_name}, {expertise}" if expertise else expert_name
    quote = excerpt(about)
    text = (
        "Dzień dobry,\n\n"
        f"Ekspert współpracujący z ROPS w Krakowie ({who}) napisał opinię "
        f"o Twoim {'pomyśle' if is_idea else 'zgłoszeniu'} w HubMi.\n\n"
        f"{label}:\n„{quote}”\n\n"
        f"Opinia:\n{body}\n\n"
        f"Całą rozmowę zobaczysz i odpowiesz na nią tutaj:\n{thread_url}\n\n"
        f"{SIGNATURE}\n\n"
        f"{CONSENT_NOTE}"
    )
    html = html_document(
        subject,
        f"{H1}Opinia eksperta</h1>"
        '<p style="margin:0 0 16px">Ekspert współpracujący z ROPS w Krakowie '
        f"(<strong>{escape(who)}</strong>) napisał opinię.</p>"
        f'<h2 style="font-size:16px;margin:0 0 8px">{label}</h2>'
        f"{html_quote(quote)}"
        '<h2 style="font-size:16px;margin:0 0 8px">Opinia</h2>'
        f"{html_paragraphs(body)}"
        f"{html_button(thread_url, 'Zobacz rozmowę i odpowiedz')}"
        f"{html_paragraphs(SIGNATURE)}"
        '<p style="margin:24px 0 0;font-size:13px;color:#57534e">'
        f"{CONSENT_NOTE}</p>",
    )
    return Email(
        to=to, subject=subject, text=text, html=html, idempotency_key=idempotency_key
    )


def expert_assigned(  # noqa: PLR0913
    *, to: str, expert_name: str, title: str, note: str | None, url: str, key: str
) -> Email:
    subject = "HubMi: prośba ROPS o Twoją opinię"
    title = excerpt(title, 200)
    note_text = f"Uwagi od ROPS:\n{note}\n\n" if note else ""
    text = (
        f"Dzień dobry, {expert_name},\n\n"
        "zespół ROPS w Krakowie prosi o Twoją opinię w HubMi.\n\n"
        f"Sprawa:\n„{title}”\n\n"
        f"{note_text}"
        f"Otwórz sprawę w panelu:\n{url}\n\n"
        f"{SIGNATURE}"
    )
    note_html = (
        '<h2 style="font-size:16px;margin:0 0 8px">Uwagi od ROPS</h2>'
        f"{html_paragraphs(note)}"
        if note
        else ""
    )
    html = html_document(
        subject,
        f"{H1}Prośba o opinię</h1>"
        f'<p style="margin:0 0 16px">Dzień dobry, {escape(expert_name)}, '
        "zespół ROPS w Krakowie prosi o Twoją opinię w HubMi.</p>"
        '<h2 style="font-size:16px;margin:0 0 8px">Sprawa</h2>'
        f"{html_quote(title)}"
        f"{note_html}"
        f"{html_button(url, 'Otwórz sprawę w panelu')}"
        f"{html_paragraphs(SIGNATURE)}",
    )
    return Email(to=to, subject=subject, text=text, html=html, idempotency_key=key)
