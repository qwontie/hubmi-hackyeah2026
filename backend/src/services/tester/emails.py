from services.mail import Email
from services.mail.templates import (
    CONSENT_NOTE,
    H1,
    SIGNATURE,
    excerpt,
    html_button,
    html_document,
    html_paragraphs,
    html_quote,
)

REASON_SLOT = "{reason}"
REPORT_BUTTON = "Otwórz formularz raportu"


def accept_draft(title: str) -> str:
    return (
        "Dzień dobry,\n\n"
        f"dziękujemy za zgłoszenie. Z przyjemnością zapraszamy do przetestowania "
        f"rozwiązania „{title}” zgodnie z przesłaną propozycją.\n\n"
        "Po teście prosimy o krótki raport: co udało się zrobić i z kim, "
        "co zadziałało, a co warto zmienić. Formularz otwiera się z linku poniżej, "
        "bez zakładania konta. Raport można poprawiać, dopóki go nie zamkniemy.\n\n"
        "W razie pytań wystarczy odpowiedzieć na tę wiadomość."
    )


def reject_draft(title: str) -> str:
    return (
        "Dzień dobry,\n\n"
        f"dziękujemy za zgłoszenie chęci przetestowania rozwiązania „{title}” "
        "i za poświęcony czas. Tym razem nie możemy go przyjąć.\n\n"
        f"Powód: {REASON_SLOT}\n\n"
        "Zachęcamy do zgłoszeń do innych rozwiązań w HubMi. "
        "W razie pytań wystarczy odpowiedzieć na tę wiadomość."
    )


def _email(
    *, to: str, subject: str, body: str, link: str | None, idempotency_key: str
) -> Email:
    text = body
    if link:
        text += f"\n\nFormularz raportu:\n{link}"
    text += f"\n\n{SIGNATURE}\n\n{CONSENT_NOTE}"
    html = html_document(
        subject,
        f"{H1}{subject}</h1>"
        f"{html_paragraphs(body)}"
        f"{html_button(link, REPORT_BUTTON) if link else ''}"
        f"{html_paragraphs(SIGNATURE)}"
        '<p style="margin:24px 0 0;font-size:13px;color:#57534e">'
        f"{CONSENT_NOTE}</p>",
    )
    return Email(
        to=to, subject=subject, text=text, html=html, idempotency_key=idempotency_key
    )


def confirmation(*, to: str, title: str, proposal: str, key: str) -> Email:
    subject = "Dziękujemy za zgłoszenie do testu"
    quote = excerpt(proposal)
    body = (
        "Dzień dobry,\n\n"
        f"dziękujemy za zgłoszenie chęci przetestowania rozwiązania „{title}”. "
        "Pracownik ROPS przeczyta je osobiście i odpisze na ten adres: "
        "zaprosi do testu albo wyjaśni, dlaczego tym razem się nie uda."
    )
    text = f"{body}\n\nTwoja propozycja:\n„{quote}”\n\n{SIGNATURE}\n\n{CONSENT_NOTE}"
    html = html_document(
        subject,
        f"{H1}{subject}</h1>"
        f"{html_paragraphs(body)}"
        '<h2 style="font-size:16px;margin:0 0 8px">Twoja propozycja</h2>'
        f"{html_quote(quote)}"
        f"{html_paragraphs(SIGNATURE)}"
        '<p style="margin:24px 0 0;font-size:13px;color:#57534e">'
        f"{CONSENT_NOTE}</p>",
    )
    return Email(to=to, subject=subject, text=text, html=html, idempotency_key=key)


def accepted(*, to: str, body: str, link: str, key: str) -> Email:
    return _email(
        to=to,
        subject="Zaproszenie do testu rozwiązania",
        body=body,
        link=link,
        idempotency_key=key,
    )


def rejected(*, to: str, body: str, key: str) -> Email:
    return _email(
        to=to,
        subject="Odpowiedź na zgłoszenie do testu",
        body=body,
        link=None,
        idempotency_key=key,
    )


def message(*, to: str, body: str, link: str | None, key: str) -> Email:
    return _email(
        to=to,
        subject="Wiadomość od ROPS w sprawie testu",
        body=body,
        link=link,
        idempotency_key=key,
    )
