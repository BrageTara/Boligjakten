# Finn Tracker — Web Design Spec
**Dato:** 2026-04-21

## Oversikt

Lokal nettside for daglig oppfølging av leilighetsmarkedet i Trondheim. Leser data fra `finn_tracker.db` (SQLite) som populeres av `finn_tracker_db.py`. Bygget med Flask + HTMX.

---

## Arkitektur

```
finn_tracker.db   ← datakilde (scraper fyller denne)
app.py            ← Flask-server, alle routes
templates/
    base.html     ← felles layout (nav, stats-bar)
    index.html    ← annonseoversikt (sidebar + liste)
    detalj.html   ← enkeltannonse
static/
    style.css     ← egendefinert CSS
```

**Stack:**
- **Flask** — Python-webserver, håndterer routes og henter data fra SQLite
- **Jinja2** — templating (innebygd i Flask)
- **HTMX** — filtrering og sortering uten å skrive JavaScript
- **SQLite** — databasen `finn_tracker.db`

---

## Sider

### 1. Hovedside (`/`)

**Layout:** Sidebar til venstre + annonsekort til høyre.

**Stats-bar øverst:**
- Totalt antall annonser
- Nye i dag
- Antall flaggede
- Antall prisnedsatte

**Navigasjon:**
- Annonser (aktive)
- Solgte
- Prishistorikk

**Filterpanel (sidebar):**
| Filter | Type |
|---|---|
| Pris (min/maks) | Tallfelter |
| Område/nabolag | Nedtrekksliste |
| Størrelse BRA (min/maks) | Tallfelter |
| Antall rom | Knapper: Alle / 1 / 2 / 3+ |
| Flagg | Avkrysningsbokser (flervalg) |
| Status | Avkrysningsbokser: Aktiv / Solgt / Trukket |

Filtre sender HTMX-forespørsel til `/annonser` og oppdaterer listen uten sidereload.

**Annonsekort:**
Hvert kort viser:
- Adresse (fet) + totalpris (blå, høyre)
- Område · m² · rom · dager på Finn
- Flagg-badges (fargekodet): Prisnedsatt (gul), 14+ dager (rød), 2+ visninger (rød), Høy fellesgjeld (gul)
- Nye annonser: grønn bakgrunn + "NY"-badge

Sortering: Nyeste først (standard), Pris stigende/synkende, Dager på Finn.

**Antall resultater** vises over listen: "Viser X av Y annonser".

### 2. Detaljside (`/annonse/<finnkode>`)

Viser alle felt for én annonse:
- Adresse og lenke til Finn.no
- Prisantydning, fellesgjeld, totalpris, kr/m²
- Felleskost/mnd, fellesformue
- Boligtype, BRA, rom, etasje
- Første gang sett, sist oppdatert, dager på Finn
- Antall visninger, neste visning
- Startpris, prisendring
- Megler og meglerkontor
- Flagg
- Prishistorikk som enkel tabell (dato → pris)

Tilbake-knapp til listen.

---

## Dataflyt

```
Nettleser → GET / → Flask henter fra SQLite → Jinja2 renderer index.html
Bruker justerer filter → HTMX POST /annonser → Flask henter filtrert data → returnerer bare liste-HTML → HTMX erstatter listen i DOM
Bruker klikker annonse → GET /annonse/<finnkode> → Flask henter rad + prishistorikk → renderer detalj.html
```

---

## Feilhåndtering

- Hvis `finn_tracker.db` ikke finnes: vis feilmelding "Databasen er ikke opprettet ennå — kjør finn_tracker_db.py først."
- Hvis en finnkode ikke finnes: returner 404 med enkel feilside.

---

## Ikke i scope (foreløpig)

- Brukerinnlogging
- Kart
- Mobiloptimalisering
- Deployment til sky
