# Design: Nybygg-støtte — scraper, filter og histogram

**Dato:** 2026-04-21
**Status:** Godkjent

---

## Bakgrunn

Scraperen henter i dag kun bruktboliger (`is_new_property=false`). Ønsket er å hente alle boliger i Trondheim, skille mellom brukt og nybygg, la brukeren filtrere på type, og vise nybygg som egne segmenter i kr/m²-histogrammet.

---

## Del 1 — Scraper

### Endring i SEARCH_URL

Fjern `is_new_property=false` fra `SEARCH_URL` i `scraper.py`. Finn.no returnerer da både brukt og nybygg i samme søk.

```python
SEARCH_URL = (
    "https://www.finn.no/realestate/homes/search.html"
    "?location=1.20016.20318"
    "&sort=PUBLISHED_DESC"
)
```

### Deteksjon av boligtype

Finn.no-URL-er inneholder enten `/homes/` (brukt) eller `/newbuildings/` (nybygg). Boligtypen leses direkte fra URL-en i `fetch_all_listings()` og lagres per listing-objekt.

```python
er_nybygg = 1 if "/newbuildings/" in href else 0
```

### Ny databasekolonne

Legg til kolonne `er_nybygg INTEGER DEFAULT 0` i `annonser`-tabellen. Eksisterende rader migreres automatisk (DEFAULT 0 = brukt).

### Histogram-data

Histogram-bins i `omrade_stats.histogram_json` utvides med to nye felt:

```json
{
  "label": "30-35k",
  "aktive": 5,
  "solgte": 3,
  "ny_aktive": 2,
  "ny_solgte": 1
}
```

Scraper-logikken som bygger histogrammet i `finn_tracker_db.py` oppdateres til å telle `er_nybygg = 0` og `er_nybygg = 1` separat per bin.

---

## Del 2 — Filter i nettsiden

### Toggle-knapper

To toggle-knapper legges til i filterpanelet i `index.html`:

- **[Brukt]** — aktiv som standard
- **[Nybygg]** — inaktiv som standard

Knappene kan slås av/på uavhengig av hverandre. Standardtilstand viser kun bruktboliger (som i dag).

### Backend-filter

`get_listings()` i `db.py` får ny støtte for `er_nybygg`-filter:

- Valgte typer sendes som liste (`["0"]`, `["1"]`, eller `["0", "1"]`)
- Genererer WHERE-klausul: `er_nybygg IN (0, 1)` (tilpasset valg)
- Default (ingen valg): `er_nybygg = 0` (kun brukt)

### HTMX

Filteret sendes via eksisterende POST til `/annonser` — ingen nye ruter nødvendig.

---

## Del 3 — Histogram

### Fire segmenter per søyle

Hver søyle i histogrammet viser 4 segmenter stablet fra bunn:

| Segment | Farge |
|---|---|
| Brukt aktiv | Blå (eksisterende) |
| Brukt solgt siste 12 mnd | Oransje (eksisterende) |
| Nybygg aktiv | Lysegrønn (`#4ade80`) |
| Nybygg solgt siste 12 mnd | Mørkegrønn (`#16a34a`) |

### Klikkbar legende

Legendelementene er klikkbare og toggler tilhørende segment av/på i alle søylene. Implementeres med ren JavaScript (ingen server-kall). Klikker man på f.eks. "Nybygg solgt" forsvinner de mørkegrønne segmentene fra alle søylene umiddelbart.

Visuelt markeres deaktivert segment med redusert opacity på legendeknappen.

---

## Berørte filer

| Fil | Endring |
|---|---|
| `scraper.py` | Fjern `is_new_property=false` fra URL, legg til `er_nybygg` i listing-objekt |
| `finn_tracker_db.py` | Migrer DB-skjema, lagre `er_nybygg`, oppdater histogram-bygging |
| `db.py` | Legg til `er_nybygg`-filter i `get_listings()` |
| `app.py` | Send `er_nybygg`-filter fra POST-data videre |
| `templates/index.html` | Legg til toggle-knapper for Brukt/Nybygg |
| `templates/omrade_histogram.html` | Legg til 2 nye segmenter + klikkbar legende med JS |
| `static/style.css` | Legg til farger for lysegrønn og mørkegrønn |
