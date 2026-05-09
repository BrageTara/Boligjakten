# Implementation Plan: Interactive Map Page

**Spec:** `docs/superpowers/specs/2026-05-09-interactive-map-design.md`
**Date:** 2026-05-09

---

## Order of operations

The plan groups work into four phases. Each phase delivers something that can be checked end-to-end before moving on.

### Phase 1 — Coordinates in the database

1. **Schema migration** — `init_db()` adds `lat REAL, lon REAL` to `annonser` and `solgte` (idempotent: check `PRAGMA table_info` first so existing DBs upgrade silently).
2. **Scraper extraction** — in `scraper.py` `parse_listing()`, regex on `lat=…&lon=…` from the embedded `mapUrl`, store as floats in `data["lat"]`/`data["lon"]`.
3. **UPSERT wiring** — add lat/lon to the INSERT and `ON CONFLICT DO UPDATE SET` clause in `process_listings()` (and the equivalent for `solgte`).
4. **Backfill script** — `tools/backfill_coords.py` walks rows where `lat IS NULL`, hits each listing URL, regex-extracts coords, writes them back. Polite delay, resumable, prints progress.

**Done when:** The scraper extracts coords for new ads, and the backfill has populated coords for the existing 1487 active rows.

### Phase 2 — Backend

5. **`get_listings_with_coords(filters)` in `db.py`** — same filter contract as `get_listings()`, plus `AND lat IS NOT NULL AND lon IS NOT NULL`. Returns the slim column set the map needs.
6. **`/kart` route** — renders `kart.html` with `stats`, `omrader`, `today_str` (same context as `/`).
7. **`POST /kart/markers` route** — reads filter form data (reusing the `clean_price` helper and the same field names as `/annonser`), calls `get_listings_with_coords`, returns JSON.

**Done when:** `curl -X POST /kart/markers` returns the expected list of slim listing dicts.

### Phase 3 — Frontend

8. **`templates/kart.html`** — extends `base.html`. Layout reuses the `.layout` + `.sidebar` shell; main column is a `<div id="map">` taking the available height. The sidebar duplicates the filter form from `index.html` but with `hx-post="/kart/markers"` (or a plain JS fetch — see step 11).
9. **Leaflet integration in `static/map.js`** — load OSM tiles, init map at Trondheim sentrum zoom 12. Wire up the markercluster plugin from CDN.
10. **Marker rendering** — fetch the initial dataset on page load, render coloured circle markers (5-step green→red colour scale based on global P10/P30/P50/P70/P90 of `kvm_pris`). Listings without `kvm_pris` get a neutral grey marker.
11. **Filter wiring** — listen for changes on the form (mirror the `change, input delay:400ms` trigger from the listings page), POST as form data to `/kart/markers`, replace the marker layer with the response.
12. **Click popup** — adresse, område, kr/m², totalpris, BRA, rom, flagg-badges, "Se detaljer →" link to `/annonse/<finnkode>`.
13. **Nav link** — add `Kart` to `templates/base.html` between `Annonser` and `Områder`.

**Done when:** Visiting `/kart` shows clustered, colour-coded markers; filters update them; clicking a marker shows the popup; the detail link navigates correctly.

### Phase 4 — Tests + polish

14. **Backend tests** — query (filters apply, NULL coords excluded), route (200, JSON shape), filter strip + spaces.
15. **Manual checks** — verify in browser: clustering at city scale, colour gradient looks reasonable, popup link works, sidebar filters update markers, edge cases (zero results, all in one area).
16. **Changelog entry** — under today's date.

---

## Files touched

| File | Change |
|---|---|
| `scraper.py` | regex for lat/lon |
| `finn_tracker_db.py` | schema migration, UPSERT additions |
| `tools/backfill_coords.py` | NEW — one-shot backfill script |
| `db.py` | NEW `get_listings_with_coords()` |
| `app.py` | `/kart` + `/kart/markers` routes |
| `templates/kart.html` | NEW |
| `templates/base.html` | nav link |
| `static/map.js` | NEW — Leaflet logic |
| `static/style.css` | minor tweaks for `.map-page` height |
| `tests/test_db.py` | tests for new query |
| `tests/test_routes.py` | tests for new routes |

---

## Risks + mitigations

- **Finn changes embed format** — coords are in `mapUrl` today; if they move it, the regex stops matching. Falls back to `None` (listing is silently dropped from the map). Easy to fix when noticed.
- **Backfill rate-limiting** — Finn could throttle if we hit too fast. 0.5 s between requests + a User-Agent matching the existing scraper should be fine. Script is resumable if it gets interrupted.
- **Map performance with 1500 markers** — `markercluster` handles this comfortably (designed for tens of thousands).
- **Address-only listings** — some "tomtekjøp" or hidden-address listings may have no `mapUrl`. They simply won't appear on the map; nothing else breaks.

---

## Tasks

Implementation tasks live as one `.md` per step in `notes/tasks/`, prefixed `kart-N-…`, in the order above.
