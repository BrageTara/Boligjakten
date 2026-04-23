# Design Spec: Average and Median Lines on Price Histogram

**Date:** 2026-04-23
**Status:** Approved

---

## Overview

Add two vertical dotted lines to the kr/m² histogram on the area pages — one for average and one for median. The lines reflect the currently visible segment filter (Brukt / Nybygg / all).

---

## Section 1 — Data (scraper)

**File:** `finn_tracker_db.py` → `update_omrade_stats()`

After building the histogram bins, calculate and store the following additional fields inside `histogram_json`:

| Field | Description |
|---|---|
| `brukt_avg` | Mean kr/m² of all non-nybygg listings (aktive + solgte) |
| `brukt_median` | Median kr/m² of all non-nybygg listings |
| `ny_avg` | Mean kr/m² of all nybygg listings (ny_aktive + ny_solgte) |
| `ny_median` | Median kr/m² of all nybygg listings |
| `alle_avg` | Mean kr/m² of all listings combined |
| `alle_median` | Median kr/m² of all listings combined |
| `bin_start` | Starting kr/m² value of the first bin (integer) |

These values are calculated from the raw `kvm_pris` lists already in memory at the time `update_omrade_stats()` runs. If a segment has no data (empty list), its avg/median is `null`.

The `bin_start` value is needed by JS to convert a kr/m² price to a horizontal position percentage:

```
left% = (value - bin_start) / (num_bins × BIN_SIZE) × 100
```

where `BIN_SIZE = 2000`.

---

## Section 2 — Rendering (template + CSS)

**Files:** `templates/omrade_histogram.html`, `static/style.css`

### HTML

- Add `position: relative` to `.histogram-bars` in CSS.
- Render two absolutely positioned `div`s inside `.histogram-bars` (after the bar columns):
  - `.hist-avg-line` — for the average
  - `.hist-median-line` — for the median
- Each line spans the full height of the bar area (`top: 0; bottom: 0`).
- Each line has a small label at the top showing the value, e.g. `Snitt: 45k` / `Median: 43k`.
- Initial `left%` is calculated server-side using `alle_avg` / `alle_median` and injected as inline style.
- If a value is `null` (no data for that segment), the line is hidden (`display: none`).

### CSS

```css
.hist-avg-line {
  position: absolute;
  top: 0; bottom: 0;
  border-left: 2px dotted #a855f7;  /* purple */
  pointer-events: none;
}

.hist-median-line {
  position: absolute;
  top: 0; bottom: 0;
  border-left: 2px dotted #f59e0b;  /* amber */
  pointer-events: none;
}

.hist-line-label {
  position: absolute;
  top: 2px;
  left: 4px;
  font-size: 9px;
  white-space: nowrap;
}
```

### Legend

Add two entries to the existing `.hist-legend` row:
- Purple dot + "Snitt"
- Amber dot + "Median"

These are display-only (no toggle behaviour).

---

## Section 3 — JS logic (filter-aware updates)

**File:** `templates/omrade_histogram.html` (inline `<script>`)

### Passing stats to the template

`app.py` already passes `bins` and `max_count` to `omrade_histogram.html`. The route is extended to also pass a `stats` dict containing the new fields:

```python
return render_template("omrade_histogram.html",
    bins=data["bins"], max_count=data["max_count"], omrade=omrade, stats=data)
```

The same applies to `detalj.html`, which calls `get_omrade_histogram_cached()` and passes the result directly — `stats` is added there too.

### Stats object

The stats (avg/median values + bin_start + num_bins) are embedded in the page as a JS object via a `<script>` tag rendered by Jinja2:

```js
const histStats = {
  bin_start: {{ stats.bin_start }},
  num_bins: {{ bins | length }},
  brukt_avg: {{ stats.brukt_avg or 'null' }},
  brukt_median: {{ stats.brukt_median or 'null' }},
  ny_avg: {{ stats.ny_avg or 'null' }},
  ny_median: {{ stats.ny_median or 'null' }},
  alle_avg: {{ stats.alle_avg or 'null' }},
  alle_median: {{ stats.alle_median or 'null' }},
};
```

### Update function

A helper `updateHistLines()` is called:
- On page load (initial render)
- After each call to `toggleHistSeg()`

Logic:

```
bruktVisible = brukt-aktiv OR brukt-solgt segment is visible
nyVisible    = ny-aktiv OR ny-solgt segment is visible

if bruktVisible AND NOT nyVisible  → use brukt_avg, brukt_median
if nyVisible    AND NOT bruktVisible → use ny_avg, ny_median
if NEITHER visible                 → hide both lines
otherwise (all or mixed)           → use alle_avg, alle_median
```

Position calculation:

```js
function priceToLeft(price) {
  return (price - histStats.bin_start) / (histStats.num_bins * 2000) * 100;
}
```

If a computed value is `null`, hide the corresponding line.

---

## Out of scope

- Interactive tooltips on hover over the lines
- Separate lines per segment type (one avg per segment colour)
