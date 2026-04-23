# Histogram Avg/Median Lines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add purple (average) and amber (median) vertical dotted lines to the kr/m² histogram, with small labels, that update when the Brukt/Nybygg legend is toggled.

**Architecture:** The scraper pre-calculates avg/median per segment (brukt/nybygg/alle) and stores them in `histogram_json` alongside the bins. The template renders two absolutely-positioned line `div`s initially at the "alle" values. A JS `updateHistLines()` function recalculates which stats to show whenever a legend segment is toggled.

**Tech Stack:** Python `statistics` stdlib, SQLite JSON, Flask/Jinja2, vanilla JS, CSS absolute positioning.

---

## Files Modified

| File | Change |
|---|---|
| `finn_tracker_db.py` | Add `statistics` import; extend `build_bins` to return `bin_start`; add avg/median calc; store dict in `histogram_json` |
| `db.py` | Update `get_omrade_histogram_cached` to parse new dict format and return new fields |
| `app.py` | Pass `stats=data` in both `omrade_histogram` and `detalj` routes |
| `templates/detalj.html` | Add `stats=histogram` to `{% with %}` block |
| `templates/omrade_histogram.html` | Add line divs, JS stats object, `updateHistLines()`, legend entries |
| `static/style.css` | Add `.hist-avg-line`, `.hist-median-line`, `.hist-line-label` |
| `tests/test_db.py` | Add tests for `update_omrade_stats` new fields + `get_omrade_histogram_cached` new fields |
| `tests/conftest.py` | Update seeded fixture `omrade_stats` row to use new `histogram_json` dict format |

---

## Task 1: Write failing test for `update_omrade_stats` new fields

**Files:**
- Modify: `tests/test_db.py`

- [ ] **Step 1: Add the test**

Append to `tests/test_db.py`:

```python
import sqlite3
import json
from datetime import date
from finn_tracker_db import update_omrade_stats


def test_update_omrade_stats_histogram_json_includes_avg_median_bin_start():
    # PSEUDOCODE:
    # 1. Create an in-memory SQLite DB with the required tables
    # 2. Insert known listings: 2 brukt aktive, 1 brukt solgt, 1 nybygg aktiv
    # 3. Call update_omrade_stats(conn)
    # 4. Read back histogram_json and assert it includes the new fields with expected values
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE annonser (
            finnkode TEXT, omrade TEXT, totalpris INTEGER, bra TEXT,
            er_nybygg INTEGER DEFAULT 0, status TEXT
        );
        CREATE TABLE solgte (
            finnkode TEXT, omrade TEXT, totalpris INTEGER, bra TEXT,
            er_nybygg INTEGER DEFAULT 0, solgt_dato DATE
        );
        CREATE TABLE omrade_stats (
            omrade TEXT PRIMARY KEY, antall_aktive INTEGER DEFAULT 0,
            antall_solgte INTEGER DEFAULT 0, snitt_kvm_pris INTEGER,
            min_kvm_pris INTEGER, max_kvm_pris INTEGER,
            histogram_json TEXT, oppdatert DATE
        );
    """)
    today = str(date.today())
    # totalpris / bra = kvm_pris: 4000000/50=80000, 6000000/50=120000
    conn.execute("INSERT INTO annonser VALUES ('A','TestOmrade',4000000,'50',0,'Aktiv')")
    conn.execute("INSERT INTO annonser VALUES ('B','TestOmrade',6000000,'50',0,'Aktiv')")
    # brukt solgt: 5000000/50=100000
    conn.execute(f"INSERT INTO solgte VALUES ('C','TestOmrade',5000000,'50',0,'{today}')")
    # nybygg aktiv: 7000000/50=140000
    conn.execute("INSERT INTO annonser VALUES ('D','TestOmrade',7000000,'50',1,'Aktiv')")
    conn.commit()

    update_omrade_stats(conn)

    row = conn.execute("SELECT histogram_json FROM omrade_stats WHERE omrade='TestOmrade'").fetchone()
    assert row is not None
    data = json.loads(row["histogram_json"])

    assert isinstance(data, dict), "histogram_json should now be a dict, not a list"
    assert "bins" in data
    assert "bin_start" in data
    assert data["bin_start"] == 80000  # min(80000,120000,100000,140000) floored to BIN_SIZE

    # brukt = [80000, 120000, 100000] → avg=100000, median=100000
    assert data["brukt_avg"] == 100000
    assert data["brukt_median"] == 100000

    # nybygg = [140000] → avg=140000, median=140000
    assert data["ny_avg"] == 140000
    assert data["ny_median"] == 140000

    # alle = [80000, 120000, 100000, 140000] → avg=110000, median=110000
    assert data["alle_avg"] == 110000
    assert data["alle_median"] == 110000

    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_db.py::test_update_omrade_stats_histogram_json_includes_avg_median_bin_start -v
```

Expected: FAIL — `AssertionError: histogram_json should now be a dict, not a list` (or similar import error if `statistics` is missing).

---

## Task 2: Implement new fields in `update_omrade_stats`

**Files:**
- Modify: `finn_tracker_db.py`

- [ ] **Step 1: Add `statistics` import**

In `finn_tracker_db.py`, find the imports block at the top and add `statistics`:

```python
import sqlite3
import re
import os
import json
import statistics
from datetime import date, datetime
```

- [ ] **Step 2: Change `build_bins` to return `(bins, bin_start)`**

Find the `build_bins` inner function (around line 279) and replace it entirely:

```python
    # Build histogram bins and return (bins, bin_start).
    # bin_start is the lowest bin's starting kr/m² value, needed for line positioning.
    def build_bins(aktive, solgte, ny_aktive, ny_solgte):
        # Cap outliers — values above 200k kr/m² are almost certainly data errors
        KVM_MAX = 200_000
        aktive    = [x for x in aktive    if x <= KVM_MAX]
        solgte    = [x for x in solgte    if x <= KVM_MAX]
        ny_aktive = [x for x in ny_aktive if x <= KVM_MAX]
        ny_solgte = [x for x in ny_solgte if x <= KVM_MAX]

        all_vals = aktive + solgte + ny_aktive + ny_solgte
        if not all_vals:
            return [], None
        bin_min = (min(all_vals) // BIN_SIZE) * BIN_SIZE

        # Direct binning: assign each value to its bin in one pass (O(n))
        counts = {}
        for lst_idx, lst in enumerate([aktive, solgte, ny_aktive, ny_solgte]):
            for x in lst:
                bin_idx = (x - bin_min) // BIN_SIZE
                if bin_idx not in counts:
                    counts[bin_idx] = [0, 0, 0, 0]
                counts[bin_idx][lst_idx] += 1

        # Only iterate over bins that have data — immune to outlier range issues
        bins = []
        for bin_idx in sorted(counts.keys()):
            v = bin_min + bin_idx * BIN_SIZE
            c = counts[bin_idx]
            bins.append({"label": f"{v // 1000}k", "aktive": c[0], "solgte": c[1], "ny_aktive": c[2], "ny_solgte": c[3]})
        return bins, bin_min
```

- [ ] **Step 3: Update the caller loop to use the new return value and add avg/median**

Find the block starting at `c.execute("DELETE FROM omrade_stats")` (around line 310) and replace the entire loop body:

```python
    def calc_avg(vals):
        return round(sum(vals) / len(vals)) if vals else None

    def calc_median(vals):
        return round(statistics.median(vals)) if vals else None

    print(f"  [4/4] Skriver statistikk for {len(stats)} områder...")
    c.execute("DELETE FROM omrade_stats")
    for omrade, data in stats.items():
        all_kvm = data["aktive"] + data["solgte"] + data["ny_aktive"] + data["ny_solgte"]
        if not all_kvm:
            continue
        bins, bin_start = build_bins(data["aktive"], data["solgte"], data["ny_aktive"], data["ny_solgte"])
        brukt = data["aktive"] + data["solgte"]
        nybygg = data["ny_aktive"] + data["ny_solgte"]
        histogram_data = {
            "bins": bins,
            "bin_start": bin_start,
            "brukt_avg":    calc_avg(brukt),
            "brukt_median": calc_median(brukt),
            "ny_avg":       calc_avg(nybygg),
            "ny_median":    calc_median(nybygg),
            "alle_avg":     calc_avg(all_kvm),
            "alle_median":  calc_median(all_kvm),
        }
        c.execute("""
            INSERT INTO omrade_stats
                (omrade, antall_aktive, antall_solgte, snitt_kvm_pris, min_kvm_pris, max_kvm_pris, histogram_json, oppdatert)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            omrade,
            len(data["aktive"]) + len(data["ny_aktive"]),
            len(data["solgte"]) + len(data["ny_solgte"]),
            round(sum(all_kvm) / len(all_kvm)),
            min(all_kvm),
            max(all_kvm),
            json.dumps(histogram_data),
            today,
        ))
    conn.commit()
```

- [ ] **Step 4: Also update the pseudocode comment above `update_omrade_stats`**

Replace:
```python
# PSEUDOCODE:
# 1. Query active listings — extract numeric bra, calculate kr/m² per listing, track er_nybygg
# 2. Query sold listings (past 12 months) — same
# 3. Aggregate per omrade: separate lists for aktive/solgte/ny_aktive/ny_solgte kr/m² values
# 4. For each omrade, calculate summary stats + histogram bins (2000 kr intervals, 4 fields each)
# 5. Delete all existing rows in omrade_stats
# 6. Insert one row per area including histogram_json
# 7. Commit
# Requires: init_db() must have been called before this function.
```

With:
```python
# PSEUDOCODE:
# 1. Query active listings — extract numeric bra, calculate kr/m² per listing, track er_nybygg
# 2. Query sold listings (past 12 months) — same
# 3. Aggregate per omrade: separate lists for aktive/solgte/ny_aktive/ny_solgte kr/m² values
# 4. For each omrade, calculate summary stats + histogram bins (2000 kr intervals, 4 fields each)
#    Also calculate avg and median per segment (brukt, nybygg, alle) and bin_start for line positioning
# 5. Delete all existing rows in omrade_stats
# 6. Insert one row per area with histogram_json storing bins + avg/median stats as a dict
# 7. Commit
# Requires: init_db() must have been called before this function.
```

- [ ] **Step 5: Run the failing test again — it should now pass**

```
pytest tests/test_db.py::test_update_omrade_stats_histogram_json_includes_avg_median_bin_start -v
```

Expected: PASS

- [ ] **Step 6: Run the full test suite to check for regressions**

```
pytest tests/ -v
```

Expected: all tests pass (the existing `histogram_json` tests use a manually seeded value, not `update_omrade_stats`, so they are unaffected for now).

- [ ] **Step 7: Commit**

```bash
git add finn_tracker_db.py tests/test_db.py
git commit -m "feat: store avg, median, bin_start in histogram_json for line positioning"
```

---

## Task 3: Update `get_omrade_histogram_cached` to parse new dict format

**Files:**
- Modify: `db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Write failing test for `get_omrade_histogram_cached` new fields**

Append to `tests/test_db.py`:

```python
import json as _json

def test_get_omrade_histogram_cached_returns_new_fields(seeded_app):
    # PSEUDOCODE:
    # 1. Insert a new-format histogram_json row into omrade_stats
    # 2. Call get_omrade_histogram_cached for that omrade
    # 3. Assert the returned dict includes bin_start, brukt_avg, brukt_median, etc.
    from db import get_omrade_histogram_cached
    histogram_data = {
        "bins": [{"label": "40k", "aktive": 2, "solgte": 1, "ny_aktive": 0, "ny_solgte": 0}],
        "bin_start": 40000,
        "brukt_avg": 42000, "brukt_median": 41000,
        "ny_avg": None, "ny_median": None,
        "alle_avg": 42000, "alle_median": 41000,
    }
    with seeded_app.app_context():
        from db import get_db
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO omrade_stats (omrade, histogram_json, oppdatert) VALUES (?,?,?)",
            ("NyttOmrade", _json.dumps(histogram_data), "2026-04-23")
        )
        conn.commit()
        result = get_omrade_histogram_cached("NyttOmrade")

    assert result is not None
    assert "bins" in result
    assert "max_count" in result
    assert result["bin_start"] == 40000
    assert result["brukt_avg"] == 42000
    assert result["brukt_median"] == 41000
    assert result["ny_avg"] is None
    assert result["alle_avg"] == 42000
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_db.py::test_get_omrade_histogram_cached_returns_new_fields -v
```

Expected: FAIL — `KeyError: 'bin_start'` or similar.

- [ ] **Step 3: Update `get_omrade_histogram_cached` in `db.py`**

Replace the current implementation:

```python
# PSEUDOCODE:
# 1. Read histogram_json for the given omrade from omrade_stats
# 2. Parse JSON — new format is a dict with "bins" key; old format is a plain list (backward compat)
# 3. Calculate max_count across all bins
# 4. Return dict with bins, max_count, and all new stat fields; or None if not found
def get_omrade_histogram_cached(omrade):
    conn = get_db()
    row = conn.execute(
        "SELECT histogram_json FROM omrade_stats WHERE omrade = ?", (omrade,)
    ).fetchone()
    conn.close()
    if not row or not row["histogram_json"]:
        return None
    raw = json.loads(row["histogram_json"])
    # Handle both old format (plain list) and new format (dict with "bins" key)
    if isinstance(raw, list):
        bins = raw
        extra = {"bin_start": None, "brukt_avg": None, "brukt_median": None,
                 "ny_avg": None, "ny_median": None, "alle_avg": None, "alle_median": None}
    else:
        bins = raw.get("bins", [])
        extra = {k: raw.get(k) for k in
                 ("bin_start", "brukt_avg", "brukt_median", "ny_avg", "ny_median", "alle_avg", "alle_median")}
    max_count = max(
        (b.get("aktive", 0) + b.get("solgte", 0) + b.get("ny_aktive", 0) + b.get("ny_solgte", 0))
        for b in bins
    ) if bins else 1
    return {"bins": bins, "max_count": max_count, **extra}
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_db.py::test_get_omrade_histogram_cached_returns_new_fields -v
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```
pytest tests/ -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: get_omrade_histogram_cached returns bin_start, avg, median fields"
```

---

## Task 4: Update routes and `detalj.html` to pass `stats` to template

**Files:**
- Modify: `app.py`
- Modify: `templates/detalj.html`

- [ ] **Step 1: Update the `omrade_histogram` route in `app.py`**

Find (around line 110):
```python
    @app.route("/område-histogram/<omrade>")
    def omrade_histogram(omrade):
        data = get_omrade_histogram_cached(omrade)
        if not data:
            return "<p style='color:#94a3b8; padding:12px;'>Ingen kr/m²-data for dette området.</p>"
        return render_template("omrade_histogram.html", bins=data["bins"], max_count=data["max_count"], omrade=omrade)
```

Replace with:
```python
    @app.route("/område-histogram/<omrade>")
    def omrade_histogram(omrade):
        data = get_omrade_histogram_cached(omrade)
        if not data:
            return "<p style='color:#94a3b8; padding:12px;'>Ingen kr/m²-data for dette området.</p>"
        return render_template("omrade_histogram.html",
                               bins=data["bins"], max_count=data["max_count"],
                               omrade=omrade, stats=data)
```

- [ ] **Step 2: Update the `detalj` route in `app.py`**

Find (around line 73):
```python
        histogram = get_omrade_histogram_cached(listing["omrade"]) if listing.get("omrade") else None
        return render_template("detalj.html", listing=listing, events=events, histogram=histogram)
```

This line stays unchanged — `histogram` already contains the full dict. We update how `detalj.html` passes it to the included template in the next step.

- [ ] **Step 3: Update `detalj.html` to pass `stats` in the `{% with %}` block**

In `templates/detalj.html`, find:
```html
    {% with bins=histogram.bins, max_count=histogram.max_count %}
      {% include "omrade_histogram.html" %}
    {% endwith %}
```

Replace with:
```html
    {% with bins=histogram.bins, max_count=histogram.max_count, stats=histogram %}
      {% include "omrade_histogram.html" %}
    {% endwith %}
```

- [ ] **Step 4: Run the app and spot-check**

```
python app.py
```

Navigate to `http://127.0.0.1:5000/områder`, open an area accordion, and to a detail page. Confirm no 500 errors in the terminal (lines won't appear yet — template not updated).

- [ ] **Step 5: Commit**

```bash
git add app.py templates/detalj.html
git commit -m "feat: pass stats dict to omrade_histogram template for line positioning"
```

---

## Task 5: Add CSS for the avg/median lines

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Add the new CSS classes**

In `static/style.css`, find the histogram block (after `.hist-legend-item.disabled`). Append after line `.hist-legend-item.disabled { opacity: 0.35; }`:

```css
.hist-avg-line {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: 2px dotted #a855f7;
  pointer-events: none;
  z-index: 1;
}
.hist-median-line {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: 2px dotted #f59e0b;
  pointer-events: none;
  z-index: 1;
}
.hist-line-label {
  position: absolute;
  top: 2px;
  left: 4px;
  font-size: 9px;
  white-space: nowrap;
  color: inherit;
}
.hist-avg-line .hist-line-label  { color: #a855f7; }
.hist-median-line .hist-line-label { color: #f59e0b; }
```

Also add `position: relative` to `.histogram-bars`:

Find:
```css
.histogram-bars { display: flex; align-items: flex-end; gap: 4px; height: 100px; }
```

Replace with:
```css
.histogram-bars { display: flex; align-items: flex-end; gap: 4px; height: 100px; position: relative; }
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat: add CSS for histogram avg/median dotted lines"
```

---

## Task 6: Update `omrade_histogram.html` with lines, JS stats, and `updateHistLines`

**Files:**
- Modify: `templates/omrade_histogram.html`

- [ ] **Step 1: Replace the entire template with the updated version**

```html
{% if stats and stats.bin_start is not none and stats.alle_avg %}
  {% set bin_count = bins | length %}
  {% set avg_left    = ((stats.alle_avg    - stats.bin_start) / (bin_count * 2000) * 100) | round(2) %}
  {% set median_left = ((stats.alle_median - stats.bin_start) / (bin_count * 2000) * 100) | round(2) %}
{% else %}
  {% set avg_left = none %}
  {% set median_left = none %}
{% endif %}

<div class="histogram-wrap">
  <div class="histogram-bars" id="hist-bars-{{ omrade | replace(' ', '-') }}">
    {% for bin in bins %}
      {% set total = bin.aktive + bin.solgte + bin.get('ny_aktive', 0) + bin.get('ny_solgte', 0) %}
      {% set pct = (total / max_count * 100) | round(1) %}
      {% set a_pct  = (bin.aktive / total * 100)                   | round(1) if total else 0 %}
      {% set s_pct  = (bin.solgte / total * 100)                   | round(1) if total else 0 %}
      {% set na_pct = (bin.get('ny_aktive', 0) / total * 100)      | round(1) if total else 0 %}
      {% set ns_pct = (bin.get('ny_solgte', 0) / total * 100)      | round(1) if total else 0 %}
      <div class="hist-col">
        <div class="hist-bar-wrap" style="height:{{ pct }}%;">
          <div class="hist-segment hist-aktiv"    data-seg="brukt-aktiv"  style="height:{{ a_pct }}%;"></div>
          <div class="hist-segment hist-solgt"    data-seg="brukt-solgt"  style="height:{{ s_pct }}%;"></div>
          <div class="hist-segment hist-ny-aktiv" data-seg="ny-aktiv"     style="height:{{ na_pct }}%;"></div>
          <div class="hist-segment hist-ny-solgt" data-seg="ny-solgt"     style="height:{{ ns_pct }}%;"></div>
        </div>
        <div class="hist-label">{{ bin.label }}</div>
      </div>
    {% endfor %}

    {% if avg_left is not none %}
      <div class="hist-avg-line" id="hist-avg-line-{{ omrade | replace(' ', '-') }}"
           style="left:{{ avg_left }}%;">
        <span class="hist-line-label">Snitt: {{ (stats.alle_avg / 1000) | round(0) | int }}k</span>
      </div>
    {% endif %}
    {% if median_left is not none %}
      <div class="hist-median-line" id="hist-median-line-{{ omrade | replace(' ', '-') }}"
           style="left:{{ median_left }}%;">
        <span class="hist-line-label">Median: {{ (stats.alle_median / 1000) | round(0) | int }}k</span>
      </div>
    {% endif %}
  </div>

  <div class="hist-legend">
    <span class="hist-legend-item" data-seg="brukt-aktiv" onclick="toggleHistSeg(this)">
      <span class="hist-legend-dot hist-aktiv-dot"></span> Brukt aktiv
    </span>
    <span class="hist-legend-item" data-seg="brukt-solgt" onclick="toggleHistSeg(this)" style="margin-left:12px;">
      <span class="hist-legend-dot hist-solgt-dot"></span> Brukt solgt
    </span>
    <span class="hist-legend-item" data-seg="ny-aktiv" onclick="toggleHistSeg(this)" style="margin-left:12px;">
      <span class="hist-legend-dot hist-ny-aktiv-dot"></span> Nybygg aktiv
    </span>
    <span class="hist-legend-item" data-seg="ny-solgt" onclick="toggleHistSeg(this)" style="margin-left:12px;">
      <span class="hist-legend-dot hist-ny-solgt-dot"></span> Nybygg solgt
    </span>
    {% if avg_left is not none %}
    <span style="margin-left:12px; display:inline-flex; align-items:center; gap:4px; font-size:11px; color:#64748b;">
      <span style="display:inline-block;width:10px;height:0;border-top:2px dotted #a855f7;"></span> Snitt
    </span>
    <span style="margin-left:8px; display:inline-flex; align-items:center; gap:4px; font-size:11px; color:#64748b;">
      <span style="display:inline-block;width:10px;height:0;border-top:2px dotted #f59e0b;"></span> Median
    </span>
    {% endif %}
  </div>
</div>

<script>
// toggleHistSeg must be defined globally so onclick attributes work.
// It is redefined each time a histogram partial is rendered, which is fine
// since only one histogram is interacted with at a time.
function toggleHistSeg(legendItem) {
  var seg = legendItem.dataset.seg;
  var isDisabled = legendItem.classList.toggle('disabled');
  document.querySelectorAll('[data-seg="' + seg + '"]').forEach(function(el) {
    if (el !== legendItem) {
      el.style.display = isDisabled ? 'none' : '';
    }
  });
  // updateHistLines is defined below (in the stats IIFE) and reassigned per render
  if (typeof updateHistLines === 'function') updateHistLines();
}
</script>

{% if stats and stats.bin_start is not none %}
<script>
(function() {
  var BIN_SIZE = 2000;
  var histStats = {
    bin_start:    {{ stats.bin_start }},
    bin_count:    {{ bins | length }},
    brukt_avg:    {{ stats.brukt_avg    if stats.brukt_avg    is not none else 'null' }},
    brukt_median: {{ stats.brukt_median if stats.brukt_median is not none else 'null' }},
    ny_avg:       {{ stats.ny_avg       if stats.ny_avg       is not none else 'null' }},
    ny_median:    {{ stats.ny_median    if stats.ny_median    is not none else 'null' }},
    alle_avg:     {{ stats.alle_avg     if stats.alle_avg     is not none else 'null' }},
    alle_median:  {{ stats.alle_median  if stats.alle_median  is not none else 'null' }},
  };
  var suffix = {{ omrade | replace(' ', '-') | tojson }};

  function priceToLeft(price) {
    return (price - histStats.bin_start) / (histStats.bin_count * BIN_SIZE) * 100;
  }

  function setLine(lineId, value, labelPrefix) {
    var el = document.getElementById(lineId);
    if (!el) return;
    if (value == null) {
      el.style.display = 'none';
    } else {
      el.style.display = '';
      el.style.left = priceToLeft(value).toFixed(2) + '%';
      var label = el.querySelector('.hist-line-label');
      if (label) label.textContent = labelPrefix + ': ' + Math.round(value / 1000) + 'k';
    }
  }

  // Exposed globally so toggleHistSeg (defined above) can call it
  window.updateHistLines = function() {
    var barsEl = document.getElementById('hist-bars-' + suffix);
    if (!barsEl) return;

    // Check which segment groups are currently visible
    var bruktVisible = false;
    var nyVisible = false;
    barsEl.querySelectorAll('[data-seg]').forEach(function(el) {
      if (el.classList.contains('hist-legend-item')) return;
      if (el.style.display === 'none') return;
      var seg = el.dataset.seg;
      if (seg === 'brukt-aktiv' || seg === 'brukt-solgt') bruktVisible = true;
      if (seg === 'ny-aktiv'    || seg === 'ny-solgt')    nyVisible = true;
    });

    var avg, median;
    if (bruktVisible && !nyVisible) {
      avg = histStats.brukt_avg; median = histStats.brukt_median;
    } else if (nyVisible && !bruktVisible) {
      avg = histStats.ny_avg; median = histStats.ny_median;
    } else if (!bruktVisible && !nyVisible) {
      avg = null; median = null;
    } else {
      avg = histStats.alle_avg; median = histStats.alle_median;
    }

    setLine('hist-avg-line-' + suffix, avg, 'Snitt');
    setLine('hist-median-line-' + suffix, median, 'Median');
  };

  // Run immediately to set correct initial state
  window.updateHistLines();
})();
</script>
{% endif %}
```

- [ ] **Step 2: Start the app and manually verify**

```
python app.py
```

1. Navigate to `http://127.0.0.1:5000/områder`
2. Open an area accordion — confirm the purple (Snitt) and amber (Median) dotted lines appear on the histogram with labels
3. Toggle "Brukt aktiv" off — lines should update (if both brukt segments disabled, lines switch to nybygg stats or hide)
4. Toggle all segments off — lines should hide
5. Navigate to a listing detail page with an area — confirm lines also appear in the detail page histogram

- [ ] **Step 3: Commit**

```bash
git add templates/omrade_histogram.html
git commit -m "feat: add avg/median dotted lines to histogram with filter-aware JS update"
```

---

## Task 7: Update `conftest.py` seeded fixture for new histogram_json format

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Update the seeded `omrade_stats` table schema and any seed data**

The `conftest.py` `seeded_app` fixture creates an `omrade_stats` table but does not insert any histogram rows. No change needed there.

However, if any route test asserts histogram rendering, those tests rely on `get_omrade_histogram_cached` returning data. Since no histogram rows are seeded, those tests are unaffected.

Verify this is the case:

```
pytest tests/ -v
```

Expected: all tests pass. No action needed if they do.

- [ ] **Step 2: Final full test run**

```
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Final commit (if conftest needed changes)**

Only commit if you made changes in Step 1:

```bash
git add tests/conftest.py
git commit -m "test: update seeded fixture for new histogram_json dict format"
```
