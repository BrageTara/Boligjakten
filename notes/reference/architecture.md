---
title: Architecture Overview
type: reference
updated: 2026-04-28
---

# Architecture

A high-level map of how Boligjakten is wired together: the SQLite schema, what each Python file is responsible for, and how data flows from Finn.no into the website.

See also: [[commands]] for run commands, [[troubleshooting]] for known issues, [[Home]] for vault conventions.

---

## Overview

Boligjakten has two halves:

1. **Scraper** — a daily job that pulls apartment listings from Finn.no via Playwright and writes them to a local SQLite database.
2. **Website** — a small Flask + HTMX app that reads the same SQLite database and renders it in the browser.

The two halves never talk to each other directly. The database is the only contract between them.

```
Finn.no ──► scraper.py ──► finn_tracker_db.py ──► finn_tracker.db ──► db.py ──► app.py ──► browser
                                  │                       ▲
                                  └── _run_update.py ─────┘  (refreshes omrade_stats)
```

---

## Database (`finn_tracker.db`)

SQLite, six tables. **No indexes and no foreign keys are declared** — joins go through `finnkode` by convention.

### Tables

| Table | Rows (2026-04-28) | Purpose |
|---|---|---|
| `annonser` | 1 546 | One row per *currently tracked* apartment. Upserted on every run. |
| `solgte` | 170 | Listings that disappeared from search — copied here with a reason (Solgt / Trukket / Ukjent). |
| `prishistorikk` | 1 089 | Legacy price log (one row per apartment per run). Being migrated into `hendelser`. |
| `hendelser` | 2 021 | New event log — one row per event (price change, sold, flagged, etc.). |
| `omrade_stats` | 53 | Aggregated stats per neighborhood (count, avg/min/max kr/m², histogram JSON). |
| `run_log` | 11 | One row per scraper run — start/end time, status, counts. Used by `check_status.py`. |

### Key relationships (implicit, no FKs)

```
annonser.finnkode ─┬─► prishistorikk.finnkode
                   ├─► hendelser.finnkode
                   └─► solgte.finnkode  (when status leaves "Aktiv")

annonser.omrade ──► omrade_stats.omrade
```

### `annonser` schema highlights

- **PK:** `finnkode` (TEXT)
- **Identity:** `adresse`, `type`, `bra`, `rom`, `etasje`, `omrade`, `postnummer`, `er_nybygg`
- **Pricing:** `prisantydning`, `fellesgjeld`, `totalpris`, `kvm_pris`, `felleskost`, `fellesformue`, `pris_ved_start`, `prisendring`
- **Lifecycle:** `forste_sett`, `siste_sett`, `dager_ute`, `status` (default `'Aktiv'`), `antall_visninger`, `neste_visning`
- **Misc:** `url`, `megler`, `meglerkontor`, `flagg`

Full column list lives in `init_db()` at `finn_tracker_db.py:35`.

---

## Code map

### Scraper side

| File | Lines | Responsibility |
|---|---|---|
| `scraper.py` | 316 | Pure scraping logic (Playwright). Defines `SEARCH_URL`, `POSTNUMMER` lookup, and the four core functions: `accept_cookies`, `fetch_all_listings`, `scrape_ad`, `check_sold_status`. Knows nothing about storage. |
| `finn_tracker_db.py` | 697 | The orchestrator. Owns the SQLite schema (`init_db`), upserts, sold-detection, area-stats refresh, run logging, and the `main()` entry point. **Imports from `scraper.py`.** |
| `finn_tracker.py` | 791 | Excel fallback (per CLAUDE.md, must not be deleted). Same scraping flow but writes to `finn_tracker.xlsx` via `openpyxl`. Does **not** import `scraper.py` — has its own copy of `POSTNUMMER`. |
| `_run_update.py` | 111 | Standalone refresh of `omrade_stats` (histograms etc.) without invoking Playwright. Lighter than running the full scraper. |
| `check_status.py` | 86 | Diagnostic — prints whether the scraper ran today, plus the last 5 entries from `run_log`. |

### Website side

| File | Lines | Responsibility |
|---|---|---|
| `app.py` | 128 | Flask app factory (`create_app`) and all routes. Keeps no business logic — every route just calls into `db.py` and renders a template. |
| `db.py` | 224 | All read-side SQL. One function per query (`get_stats`, `get_listings`, `get_listing`, `get_price_history`, `get_events`, `get_sold_listings`, `get_omrade_stats`, `get_omrade_histogram_cached`). Uses Flask's `current_app.config["DB_PATH"]`. |
| `templates/` | — | Jinja2: `base.html` (layout), `index.html` (main page), `listings.html` (HTMX partial), `detalj.html`, `solgte.html`, `prishistorikk.html`, `omrader.html`, `omrade_histogram.html`, `404.html`. |
| `static/style.css` | — | All site CSS. |

### Routes (in `app.py`)

| Route | Method | Renders | Purpose |
|---|---|---|---|
| `/` | GET | `index.html` | Stats bar + initial listing grid + sidebar filters. |
| `/annonser` | POST | `listings.html` | HTMX endpoint — returns just the filtered listing list. |
| `/annonse/<finnkode>` | GET | `detalj.html` | Detail page with full fields + price history + event log. |
| `/solgte` | GET | `solgte.html` | Listings that have left the active set. |
| `/prishistorikk` | GET | `prishistorikk.html` | Apartments that have changed price recently. |
| `/områder` | GET | `omrader.html` | Per-neighborhood aggregate stats. |
| `/område-histogram/<omrade>` | GET | `omrade_histogram.html` | One area's kr/m² histogram (HTMX partial). |

---

## Data flow

### Daily scrape (run by Task Scheduler at 06:00)

```
finn_tracker_db.py main()
  ├── init_db()                          (create/migrate tables if needed)
  ├── log run started → run_log
  ├── fetch_all_listings(page)           [scraper.py]
  ├── for each listing:
  │     scrape_ad(page, url)             [scraper.py]
  │     upsert_listing(conn, ...)        (annonser + hendelser)
  │     conn.commit()                    (per listing → crash-safe)
  ├── for each previously-active listing not seen this run:
  │     check_sold_status(page, url)     [scraper.py]
  │     mark_sold(conn, ...)             (move row to solgte)
  ├── update_omrade_stats(conn)          (rebuild omrade_stats incl. histograms)
  └── log run finished → run_log
```

### Web request

```
browser ──► Flask route in app.py
              └── calls db.py function (read-only SQLite query)
                    └── returns dict / list of dicts
              └── render_template(...) → HTML
```

HTMX twist: `/annonser` returns *only* `listings.html` (a fragment), which HTMX swaps into the existing page — no full reload.

---

## Open questions / known smells

Things worth discussing, not yet decided:

- **`finn_tracker_db.py` is 697 lines.** Per CLAUDE.md (>300 lines), this is split-worthy. Natural boundaries: schema/migrations → `db_init.py`, upsert/event logic → `db_writes.py`, stats → `stats.py`. Main orchestration stays in `finn_tracker_db.py`.
- **No indexes** on any table. With ~1.5k active rows it's still fast, but `hendelser.finnkode` and `prishistorikk.finnkode` will benefit from indexes as history grows.
- **`prishistorikk` ↔ `hendelser`** — there's a `migrate_prishistorikk_to_hendelser` function. Is the migration finished, or is `prishistorikk` still being written? Worth confirming before assuming it's read-only legacy.
- **`POSTNUMMER` is duplicated** between `scraper.py` and `finn_tracker.py`. If a postnummer mapping changes, both must be updated. Not urgent, but a footgun.
- **No declared foreign keys.** Orphan rows (e.g. `hendelser` for a deleted `annonser`) are possible in principle.

None of these are urgent — flagging them so we can decide together when/whether to address.
