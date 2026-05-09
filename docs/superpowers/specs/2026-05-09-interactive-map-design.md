# Design Spec: Interactive Map Page

**Date:** 2026-05-09
**Status:** Approved

---

## Overview

Add a dedicated `/kart` page that plots all active listings on an interactive map of Trondheim. Users can pan, zoom, click markers for key info, see clusters in dense areas, and filter the visible markers using the same sidebar as the main listings page. Marker colour communicates relative kr/m² so cheaper listings stand out visually.

This unblocks a question the listings table can't answer well: *"where in town are the cheap (per m²) properties right now?"*

---

## Section 1 — Coordinates (scraper)

**File:** `scraper.py` → `parse_listing()`

Finn.no embeds precise coordinates (~6 decimals, ≈10 cm) inside a `mapUrl` field in their listing JSON. Extract them via regex on the page HTML:

```
mapUrl: "...?lat=63.448576&lon=10.446552&zoom=12..."
```

Add to the returned `data` dict:

| Field | Type | Source |
|---|---|---|
| `lat` | REAL | regex on `lat=…` query param |
| `lon` | REAL | regex on `lon=…` query param |

If the regex does not match, both stay `None` — the listing simply won't appear on the map.

### DB schema change

**File:** `finn_tracker_db.py` → `init_db()`

Add `lat REAL, lon REAL` to both `annonser` and `solgte` tables. Use `ALTER TABLE … ADD COLUMN` migrations guarded by `PRAGMA table_info` so existing databases pick the columns up without manual intervention.

UPSERT in `process_listings()` writes `lat`/`lon` along with the rest of the fields.

---

## Section 2 — Backfill

**File:** `tools/backfill_coords.py` (new, one-shot)

Iterate through all `annonser` rows where `lat IS NULL`. For each, GET the listing's `url`, regex-extract lat/lon as above, write them back. Sleep 0.5 s between requests to be polite. Report progress and skip rows where the regex fails. Fully resumable — re-running just continues from the un-coorded rows.

This avoids waiting for a full re-scrape just to populate the new columns.

---

## Section 3 — Backend route + query

**File:** `db.py` → new `get_listings_with_coords(filters)`

Same filter contract as `get_listings()` but adds `AND lat IS NOT NULL AND lon IS NOT NULL` and selects only the columns the map needs:

`finnkode, adresse, omrade, lat, lon, prisantydning, totalpris, kvm_pris, bra, rom, flagg`

Returning a slim dict per row keeps the JSON payload reasonable when 1000+ markers are sent.

**File:** `app.py`

- `GET /kart` → renders `kart.html` with the same context as `/` (stats, omrader, today_str)
- `POST /kart/markers` → accepts the same form data as `/annonser`, returns JSON of filtered listings (just the slim columns above)

---

## Section 4 — Frontend

**Files:** `templates/kart.html`, `static/map.js` (new)

### Layout

Reuse the existing `.layout` + `.sidebar` shell from `index.html`. The main column hosts a single full-height map container instead of the listings list. The sidebar reuses the existing filter form, retargeted at `/kart/markers`.

### Map

- **Tiles:** OpenStreetMap via Leaflet (no API key, free)
- **Initial view:** Trondheim sentrum at zoom 12
- **CDN:** Pull Leaflet CSS+JS from the standard unpkg CDN

### Markers

- **Cluster:** Leaflet.markercluster plugin. Markers within ~80 px of each other auto-collapse to a numbered pill. Standard "spiderfy" on click at max zoom.
- **Colour:** A 5-step sequential green→red scale based on the listing's kr/m² value, computed against the global active-listing distribution (P10, P30, P50, P70, P90). Below P10 = bright green, above P90 = red. Listings without `kvm_pris` use a neutral grey.
- **Popup on click:** Address, area, kr/m², total price, BRA, room count, flags (badges), and a "Se detaljer →" link to `/annonse/<finnkode>`.

### Filter integration

When the filter form changes, fire HTMX-style `POST /kart/markers`, parse the JSON, and rebuild the marker layer. Same trigger as the listings page (`change, input delay:400ms`).

### Navigation

Add a `Kart` link in `templates/base.html` between `Annonser` and `Områder`.

---

## Section 5 — Out of scope

These are explicit non-goals for this iteration to keep scope tight:

- Drawing polygons / drawing tools / area selection
- Heatmap layer (could be a follow-up)
- Showing sold listings on the map (only `status = 'Aktiv'`)
- Mobile-specific layout (matches the rest of the app — desktop-first)
- Custom marker icons per flag (everything uses the same coloured circle)

---

## Open questions resolved during brainstorm

- **Geokoding source:** Finn.no embedded coordinates (precise to address-level, free, auto-updates with new scrapes)
- **Interaksjon:** Click popup + clusters + colour-by-kr/m². No hover tooltip (popup is enough).
- **Filtre:** Same sidebar form as the listings page, retargeted at the map endpoint.
