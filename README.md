# HubMi

Platforma Małopolskiego Hubu Innowacji Społecznych (ROPS Kraków). Mieszkaniec opisuje problem własnymi słowami, a HubMi pokazuje gotowe innowacje społeczne z Biblioteki ROPS i tłumaczy, dlaczego pasują. To samo zgłoszenie od razu trafia do pracowników ROPS, którzy widzą, z czym ludzie przychodzą, i mogą odpowiedzieć.

- aplikacja dla mieszkańców: https://hubmi.qwontie.dev
- panel ROPS: https://hubmi.qwontie.dev/admin

Projekt powstał na HackYeah 2026 w kategorii HubMI.pl.

## Jak to działa

1. Mieszkaniec, organizacja albo gmina wpisuje lub dyktuje problem, np. „tata z demencją wychodzi z domu i się gubi”.
2. System szuka po znaczeniu wśród 115 innowacji z Biblioteki ROPS i zwraca do pięciu najlepszych, każdą z jednym zdaniem uzasadnienia napisanym tylko na podstawie jej opisu.
3. Zgłoszenie dostaje numer i pojawia się w panelu ROPS bez odświeżania strony. Podobne potrzeby same układają się w teczki tematyczne z trendem.
4. Pracownik ROPS odpowiada z panelu. Autor dostaje e-mail z linkiem do rozmowy i odpisuje bez zakładania konta.

## Moduły

| Moduł | Co robi |
|---|---|
| Matchmaking | wyszukiwanie hybrydowe (wektory + polskie odmiany słów), uzasadnienia, liczba podobnych zgłoszeń |
| Zasobnik wiedzy | biblioteka innowacji, 25 wyzwań regionu z cytatem i stroną źródła, materiały ROPS ze streszczeniami, mapa powiatów |
| Kreator pomysłów | fiszka i kanwa innowacji z asystentem, wizualizacja pomysłu, generator wniosku do otwartego naboru z eksportem do PDF |
| Tester innowacji | ocena „pasuje / nie pasuje”, propozycje usprawnień, zapisy do testów |
| Komunikacja | rozmowa ROPS z autorem potrzeby lub pomysłu, opinie ekspertów, powiadomienia o naborach |
| Panel ROPS | dziennik potrzeb, teczki, edycja i import biblioteki, pomysły, testerzy, statystyki, przypisania ekspertów |
| Middleman | plan wdrożenia innowacji dla konkretnej gminy lub instytucji, bez zmyślonych liczb i przepisów |

Dostępność według WCAG 2.1 AA: pełna obsługa z klawiatury, czytniki ekranu, większy tekst, wysoki kontrast, ograniczenie ruchu, dyktowanie i odczytywanie wyników na głos.

## Stos

| Część | Katalog | Technologia |
|---|---|---|
| API | `backend/` | Python 3.13, FastAPI, SQLModel, Alembic, pydantic-ai z Gemini |
| Baza | | PostgreSQL 17 z pgvector |
| Panel ROPS | `frontend/` | SvelteKit 2, Svelte 5, Tailwind 4 |
| Aplikacja publiczna | `mobile/` | React Native z Expo, eksport na web |
| Proxy | `caddy/` | Caddy, HTTPS |

Dane pochodzą z publicznych stron rops.krakow.pl. Import jest idempotentny i nie nadpisuje poprawek wprowadzonych ręcznie w panelu.

## Uruchomienie lokalne

Potrzebne: Docker, `uv`, `bun`, klucz Gemini API.

```sh
docker network create caddy
make env
```

`make env` tworzy `.env` i pliki `docker-compose.override.yml` z wolnymi portami. W `.env` uzupełnij co najmniej `AUTH__SECRET` i `LLM__GEMINI_API_KEY`. `MAILER__RESEND_API_KEY` jest potrzebny tylko do wysyłki e-maili.

```sh
make deploy
make -C backend script library.import_rops
make -C backend script knowledge.import_rops
make -C backend script user.create -- admin <hasło>
```

`make deploy` buduje obrazy, uruchamia bazę, migracje i usługi. Pierwszy import wiedzy trwa ok. 30 minut, kolejne kilka minut.

Proxy:

```sh
cd caddy
cp Caddyfile.example Caddyfile
cp .env.example .env
docker compose up -d
```

Aplikacja działa pod http://hubmi.localhost, panel pod http://hubmi.localhost/admin.

Dane demonstracyjne ładuje osobny skrypt przez prawdziwe usługi i równie łatwo je usuwa:

```sh
make -C backend script demo.load
make -C backend script demo.wipe
```

## Dla deweloperów

`make fmt` formatuje wszystkie części, `make check` uruchamia ruff, ty, ultracite, svelte-check i tsc.

```sh
make -C frontend dev
make -C mobile dev
make -C backend revision m="opis zmiany"
```

Kopia bazy: `make backup`, przywrócenie: `make restore file=backups/hubmi-<data>.dump`.
