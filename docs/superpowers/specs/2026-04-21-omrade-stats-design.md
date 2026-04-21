# Område Statistics Page — Design Spec
**Dato:** 2026-04-21

## Overview

A new page at `/områder` showing price/m² statistics per area in Trondheim. Data is pre-calculated and cached in a new SQLite table `omrade_stats`, updated at the end of each scraper run. Uses `totalpris` for all calculations.

---

## Architecture

```
finn_tracker.db
  └── omrade_stats    ← pre-calculated stats, updated by scraper

finn_tracker_db.py    ← calls update_omrade_stats() at end of each run
db.py                 ← new get_omrade_stats() query function
app.py                ← new /områder route
templates/
    omrader.html      ← new page: table + visual bar per area
    base.html         ← add Områder link to navbar
```

---

## Database

### New table: `omrade_stats`

```sql
CREATE TABLE IF NOT EXISTS omrade_stats (
    omrade          TEXT PRIMARY KEY,
    antall_aktive   INTEGER DEFAULT 0,
    antall_solgte   INTEGER DEFAULT 0,
    snitt_kvm_pris  INTEGER,
    min_kvm_pris    INTEGER,
    max_kvm_pris    INTEGER,
    oppdatert       DATE
);
```

Recalculated from scratch on every scraper run:
- **Active listings:** `annonser` WHERE `status = 'Aktiv'` AND `totalpris IS NOT NULL` AND `bra IS NOT NULL`
- **Sold listings:** `solgte` WHERE `solgt_dato >= date('now', '-12 months')` AND `totalpris IS NOT NULL` AND `bra IS NOT NULL`
- **kr/m²** calculated as `totalpris / CAST(bra AS INTEGER)` — rows where `bra` is not a valid integer are excluded
- Areas with zero qualifying listings are excluded from the table

---

## Scraper change (`finn_tracker_db.py`)

New function `update_omrade_stats(conn)` called at the end of `main()`:

1. Delete all rows from `omrade_stats`
2. Query active listings grouped by `omrade`, calculate avg/min/max kr/m²
3. Query sold listings (past 12 months) grouped by `omrade`, calculate avg/min/max kr/m²
4. Merge results: for areas appearing in both, combine counts and recalculate weighted avg/min/max
5. Insert all rows into `omrade_stats`
6. Commit

---

## Query layer (`db.py`)

New function `get_omrade_stats(sort)`:
- Reads all rows from `omrade_stats`
- Sort options: `navn_asc` (default), `snitt_desc`, `antall_desc`
- Returns list of dicts

---

## Route (`app.py`)

```
GET /områder?sort=navn_asc
```

- Reads `sort` query param (default: `navn_asc`)
- Calls `get_omrade_stats(sort)`
- Renders `omrader.html`

---

## Template (`templates/omrader.html`)

Table with one row per area:

| Område | Aktive | Solgte (12 mnd) | Min kr/m² | Snitt kr/m² | Maks kr/m² | Spredning |
|---|---|---|---|---|---|---|
| Møllenberg | 12 | 8 | 38 000 | 52 000 | 71 000 | ████░░░ |

**Spredning bar:** A CSS bar where the filled portion represents the range min→max relative to the global min→max across all areas.

**Sort dropdown** above the table: Alfabetisk / Høyest snitt / Flest annonser.

Sort change triggers a full page reload (no HTMX needed — this page has no filters).

---

## Navbar

Add `Områder` link to `base.html` between `Solgte` and `Prisnedsatte`.

---

## Error handling

- If `omrade_stats` is empty (scraper hasn't run yet): show message "Ingen data ennå — kjør scraperen først."
- Rows where `bra` cannot be parsed as an integer are silently skipped.

---

## Out of scope

- Historical trends per area over time
- Filtering by area on this page
- Mobile layout
