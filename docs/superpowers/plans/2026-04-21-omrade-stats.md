# Område Statistics Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/områder` page showing pre-calculated price/m² statistics per area, sourced from active listings and sold listings (past 12 months), cached in a new `omrade_stats` SQLite table.

**Architecture:** A new `omrade_stats` table is populated by a new `update_omrade_stats()` function called at the end of each scraper run. The website reads from this table via a new `get_omrade_stats()` function in `db.py` and a new route in `app.py`. No HTMX needed — sort changes trigger a full page reload.

**Tech Stack:** Python 3.14, SQLite (built-in), Flask, Jinja2, pytest, pytest-flask

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `finn_tracker_db.py` | Modify | Add `omrade_stats` table creation + `update_omrade_stats()` |
| `db.py` | Modify | Add `get_omrade_stats()` query function |
| `app.py` | Modify | Add `/områder` route |
| `templates/base.html` | Modify | Add Områder link to navbar |
| `templates/omrader.html` | Create | Statistics table with spread bar |
| `tests/test_db.py` | Modify | Add tests for `get_omrade_stats()` |
| `tests/test_routes.py` | Modify | Add test for `/områder` route |
| `tests/conftest.py` | Modify | Add `omrade_stats` rows to seeded DB |

---

## Task 1: Add `omrade_stats` table and `update_omrade_stats()` to scraper

**Files:**
- Modify: `finn_tracker_db.py`

- [ ] **Step 1: Add `omrade_stats` table creation to `init_db()`**

In `finn_tracker_db.py`, inside `init_db()` after the `solgte` table creation (around line 99), add:

```python
    c.execute("""
        CREATE TABLE IF NOT EXISTS omrade_stats (
            omrade          TEXT PRIMARY KEY,
            antall_aktive   INTEGER DEFAULT 0,
            antall_solgte   INTEGER DEFAULT 0,
            snitt_kvm_pris  INTEGER,
            min_kvm_pris    INTEGER,
            max_kvm_pris    INTEGER,
            oppdatert       DATE
        )
    """)
```

- [ ] **Step 2: Write `update_omrade_stats()` function**

Add this function after `init_db()` in `finn_tracker_db.py`:

```python
# PSEUDOCODE:
# 1. Query active listings grouped by omrade — calculate count, avg/min/max totalpris/bra
#    Skip rows where bra has no parseable integer or totalpris is NULL
# 2. Query sold listings (past 12 months) grouped by omrade — same calculations
# 3. Merge both result sets: combine counts, recalculate weighted avg, overall min/max
# 4. Delete all existing rows in omrade_stats
# 5. Insert one row per area
# 6. Commit
def update_omrade_stats(conn):
    today = str(date.today())
    c = conn.cursor()

    # Query active listings — extract numeric bra with regex, calculate kr/m²
    active_rows = c.execute("""
        SELECT omrade,
               totalpris,
               CAST(TRIM(SUBSTR(bra, 1, INSTR(bra || ' ', ' ') - 1)) AS INTEGER) AS bra_num
        FROM annonser
        WHERE status = 'Aktiv'
          AND totalpris IS NOT NULL
          AND bra IS NOT NULL
          AND CAST(TRIM(SUBSTR(bra, 1, INSTR(bra || ' ', ' ') - 1)) AS INTEGER) > 0
    """).fetchall()

    # Query sold listings from past 12 months
    sold_rows = c.execute("""
        SELECT omrade,
               totalpris,
               CAST(TRIM(SUBSTR(bra, 1, INSTR(bra || ' ', ' ') - 1)) AS INTEGER) AS bra_num
        FROM solgte
        WHERE solgt_dato >= date('now', '-12 months')
          AND totalpris IS NOT NULL
          AND bra IS NOT NULL
          AND CAST(TRIM(SUBSTR(bra, 1, INSTR(bra || ' ', ' ') - 1)) AS INTEGER) > 0
    """).fetchall()

    # Aggregate into dicts keyed by omrade
    # Each entry: {"aktive": [...kvm_pris], "solgte": [...kvm_pris]}
    stats = {}
    for row in active_rows:
        if not row["omrade"]:
            continue
        kvm = round(row["totalpris"] / row["bra_num"])
        stats.setdefault(row["omrade"], {"aktive": [], "solgte": []})["aktive"].append(kvm)

    for row in sold_rows:
        if not row["omrade"]:
            continue
        kvm = round(row["totalpris"] / row["bra_num"])
        stats.setdefault(row["omrade"], {"aktive": [], "solgte": []})["solgte"].append(kvm)

    # Delete old stats and insert fresh rows
    c.execute("DELETE FROM omrade_stats")
    for omrade, data in stats.items():
        all_kvm = data["aktive"] + data["solgte"]
        if not all_kvm:
            continue
        c.execute("""
            INSERT INTO omrade_stats
                (omrade, antall_aktive, antall_solgte, snitt_kvm_pris, min_kvm_pris, max_kvm_pris, oppdatert)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            omrade,
            len(data["aktive"]),
            len(data["solgte"]),
            round(sum(all_kvm) / len(all_kvm)),
            min(all_kvm),
            max(all_kvm),
            today,
        ))
    conn.commit()
```

- [ ] **Step 3: Call `update_omrade_stats()` at the end of `main()`**

In `finn_tracker_db.py`, find the `finally:` block at the end of `main()`. Add the call just before `browser.close()`:

```python
        finally:
            update_omrade_stats(conn)
            browser.close()
            conn.close()
            print(f"\n=== Ferdig ===")
```

- [ ] **Step 4: Verify the table is created and function runs**

```bash
py -3 -c "
import sqlite3, finn_tracker_db
conn = sqlite3.connect('finn_tracker.db')
conn.row_factory = sqlite3.Row
finn_tracker_db.update_omrade_stats(conn)
rows = conn.execute('SELECT * FROM omrade_stats ORDER BY omrade LIMIT 5').fetchall()
for r in rows: print(dict(r))
conn.close()
"
```

Expected: 5 rows printed with omrade, counts, and kr/m² values.

- [ ] **Step 5: Commit**

```bash
git add finn_tracker_db.py
git commit -m "feat: add omrade_stats table and update_omrade_stats() to scraper"
```

---

## Task 2: Add `get_omrade_stats()` to `db.py` with tests

**Files:**
- Modify: `db.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: Add `omrade_stats` rows to the seeded test DB in `conftest.py`**

In `tests/conftest.py`, find the `conn.executescript("""` block inside `seeded_app`. Add the `omrade_stats` table and rows after the existing `INSERT INTO solgte` block:

```python
        CREATE TABLE omrade_stats (
            omrade TEXT PRIMARY KEY,
            antall_aktive INTEGER DEFAULT 0,
            antall_solgte INTEGER DEFAULT 0,
            snitt_kvm_pris INTEGER,
            min_kvm_pris INTEGER,
            max_kvm_pris INTEGER,
            oppdatert DATE
        );
        INSERT INTO omrade_stats VALUES
            ('Møllenberg', 5, 3, 52000, 44000, 63000, '2026-04-21'),
            ('Elgeseter',  3, 1, 58000, 51000, 67000, '2026-04-21'),
            ('Nardo',      8, 4, 41000, 35000, 49000, '2026-04-21');
```

- [ ] **Step 2: Write failing tests for `get_omrade_stats()`**

In `tests/test_db.py`, add:

```python
from db import get_stats, get_listings, get_listing, get_price_history, get_sold_listings, get_omrade_stats


def test_get_omrade_stats_returns_all_areas(seeded_app):
    with seeded_app.app_context():
        rows = get_omrade_stats("navn_asc")
    assert len(rows) == 3


def test_get_omrade_stats_sorted_alphabetically(seeded_app):
    with seeded_app.app_context():
        rows = get_omrade_stats("navn_asc")
    assert rows[0]["omrade"] == "Elgeseter"
    assert rows[1]["omrade"] == "Møllenberg"
    assert rows[2]["omrade"] == "Nardo"


def test_get_omrade_stats_sorted_by_snitt_desc(seeded_app):
    with seeded_app.app_context():
        rows = get_omrade_stats("snitt_desc")
    assert rows[0]["omrade"] == "Elgeseter"
    assert rows[-1]["omrade"] == "Nardo"


def test_get_omrade_stats_sorted_by_antall_desc(seeded_app):
    with seeded_app.app_context():
        rows = get_omrade_stats("antall_desc")
    assert rows[0]["omrade"] == "Nardo"


def test_get_omrade_stats_contains_expected_keys(seeded_app):
    with seeded_app.app_context():
        rows = get_omrade_stats("navn_asc")
    assert "antall_aktive" in rows[0]
    assert "antall_solgte" in rows[0]
    assert "snitt_kvm_pris" in rows[0]
    assert "min_kvm_pris" in rows[0]
    assert "max_kvm_pris" in rows[0]
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
py -3 -m pytest tests/test_db.py::test_get_omrade_stats_returns_all_areas -v
```

Expected: `ImportError: cannot import name 'get_omrade_stats' from 'db'`

- [ ] **Step 4: Add `get_omrade_stats()` to `db.py`**

```python
# PSEUDOCODE:
# 1. Query all rows from omrade_stats
# 2. Apply sort: navn_asc = alphabetical, snitt_desc = avg kr/m² descending,
#    antall_desc = total listings (aktive + solgte) descending
# 3. Return list of row dicts
def get_omrade_stats(sort="navn_asc"):
    sort_map = {
        "navn_asc":   "omrade ASC",
        "snitt_desc": "snitt_kvm_pris DESC",
        "antall_desc": "(antall_aktive + antall_solgte) DESC",
    }
    order = sort_map.get(sort, "omrade ASC")
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM omrade_stats ORDER BY {order}"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Run all db tests**

```bash
py -3 -m pytest tests/test_db.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add db.py tests/test_db.py tests/conftest.py
git commit -m "feat: add get_omrade_stats() query function with tests"
```

---

## Task 3: Add `/områder` route and template

**Files:**
- Modify: `app.py`
- Modify: `templates/base.html`
- Create: `templates/omrader.html`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing route test**

In `tests/test_routes.py`, add:

```python
def test_omrader_returns_200(seeded_client):
    response = seeded_client.get("/omrader")
    assert response.status_code == 200


def test_omrader_shows_area_name(seeded_client):
    response = seeded_client.get("/omrader")
    assert "Møllenberg".encode() in response.data


def test_omrader_sort_param(seeded_client):
    response = seeded_client.get("/omrader?sort=snitt_desc")
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
py -3 -m pytest tests/test_routes.py::test_omrader_returns_200 -v
```

Expected: `werkzeug.exceptions.NotFound` (route doesn't exist yet)

- [ ] **Step 3: Add `/omrader` route to `app.py`**

In `app.py`, add this route inside `create_app()` after the `prishistorikk` route:

```python
    # PSEUDOCODE:
    # 1. Read sort param from query string (default: navn_asc)
    # 2. Fetch area stats from omrade_stats table
    # 3. Calculate global min/max for the spread bar scaling
    # 4. Render omrader.html
    @app.route("/omrader")
    def omrader():
        from db import get_omrade_stats
        sort = request.args.get("sort", "navn_asc")
        rows = get_omrade_stats(sort)
        global_min = min((r["min_kvm_pris"] for r in rows), default=0)
        global_max = max((r["max_kvm_pris"] for r in rows), default=1)
        return render_template("omrader.html", rows=rows, sort=sort,
                               global_min=global_min, global_max=global_max)
```

Also add `get_omrade_stats` to the import at the top of `app.py`:

```python
from db import get_stats, get_listings, get_listing, get_price_history, get_sold_listings, get_omrade_stats
```

And remove the local import inside the route (since it's now at the top).

- [ ] **Step 4: Add Områder to navbar in `templates/base.html`**

Find the nav-links section and add the new link:

```html
  <div class="nav-links">
    <a href="{{ url_for('index') }}" class="{{ 'active' if request.endpoint == 'index' }}">Annonser</a>
    <a href="{{ url_for('solgte') }}" class="{{ 'active' if request.endpoint == 'solgte' }}">Solgte</a>
    <a href="{{ url_for('omrader') }}" class="{{ 'active' if request.endpoint == 'omrader' }}">Områder</a>
    <a href="{{ url_for('prishistorikk') }}" class="{{ 'active' if request.endpoint == 'prishistorikk' }}">Prisnedsatte</a>
  </div>
```

- [ ] **Step 5: Create `templates/omrader.html`**

```html
{% extends "base.html" %}
{% block title %}Områder — Boligjakten{% endblock %}
{% block content %}
<div style="padding:20px;">
  <h2 class="page-title">Prisstatistikk per område</h2>

  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
    <span style="font-size:12px;color:#64748b;">
      Basert på aktive annonser og solgte siste 12 måneder · kr/m² beregnet fra totalpris
    </span>
    <form method="get" action="{{ url_for('omrader') }}" style="display:flex;align-items:center;gap:8px;font-size:12px;">
      <label style="color:#64748b;">Sorter:</label>
      <select name="sort" class="sort-select" onchange="this.form.submit()">
        <option value="navn_asc"   {{ 'selected' if sort == 'navn_asc' }}>Alfabetisk</option>
        <option value="snitt_desc" {{ 'selected' if sort == 'snitt_desc' }}>Høyest snitt kr/m²</option>
        <option value="antall_desc"{{ 'selected' if sort == 'antall_desc' }}>Flest annonser</option>
      </select>
    </form>
  </div>

  {% if rows %}
    <table>
      <thead>
        <tr>
          <th>Område</th>
          <th>Aktive</th>
          <th>Solgte (12 mnd)</th>
          <th>Min kr/m²</th>
          <th>Snitt kr/m²</th>
          <th>Maks kr/m²</th>
          <th>Spredning</th>
        </tr>
      </thead>
      <tbody>
        {% for r in rows %}
          {% set range = global_max - global_min if global_max > global_min else 1 %}
          {% set bar_start = ((r.min_kvm_pris - global_min) / range * 100) | int %}
          {% set bar_width = ((r.max_kvm_pris - r.min_kvm_pris) / range * 100) | int %}
          {% set dot_pos   = ((r.snitt_kvm_pris - global_min) / range * 100) | int %}
          <tr>
            <td style="font-weight:600;">{{ r.omrade }}</td>
            <td>{{ r.antall_aktive }}</td>
            <td>{{ r.antall_solgte }}</td>
            <td>{{ "{:,.0f}".format(r.min_kvm_pris).replace(",", " ") }}</td>
            <td style="font-weight:600;">{{ "{:,.0f}".format(r.snitt_kvm_pris).replace(",", " ") }}</td>
            <td>{{ "{:,.0f}".format(r.max_kvm_pris).replace(",", " ") }}</td>
            <td style="width:160px;">
              <div style="position:relative;height:10px;background:#e2e8f0;border-radius:5px;">
                <div style="position:absolute;left:{{ bar_start }}%;width:{{ bar_width }}%;height:100%;background:#bfdbfe;border-radius:5px;"></div>
                <div style="position:absolute;left:{{ dot_pos }}%;transform:translateX(-50%);width:8px;height:10px;background:#1d4ed8;border-radius:2px;"></div>
              </div>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
    <p style="margin-top:12px;font-size:11px;color:#94a3b8;">
      Spredningsbar: lys blå = min→maks, mørk blå = snitt
    </p>
  {% else %}
    <p style="color:#94a3b8;">Ingen data ennå — kjør scraperen først.</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 6: Run all tests**

```bash
py -3 -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Verify manually**

```bash
py -3 app.py
```

Open http://localhost:5000/omrader — confirm:
- Table shows areas with counts and kr/m² values
- Spread bar is visible per row
- Sort dropdown changes the order
- Navbar shows "Områder" link

- [ ] **Step 8: Commit**

```bash
git add app.py templates/base.html templates/omrader.html tests/test_routes.py
git commit -m "feat: add omrader page with price/m² stats per area"
```

---

## Self-Review

**Spec coverage:**
- ✅ New page at `/områder`
- ✅ `omrade_stats` table with all required columns
- ✅ Active + sold listings (past 12 months) both used
- ✅ Uses `totalpris` for calculations
- ✅ `update_omrade_stats()` called at end of scraper run
- ✅ Sort options: alphabetical (default), avg kr/m², number of listings
- ✅ Spread bar showing min/avg/max
- ✅ Navbar link added
- ✅ Empty state message

**Placeholder scan:** None found.

**Type consistency:**
- `get_omrade_stats(sort)` defined in Task 2 Step 4, imported in Task 3 Step 3 — consistent.
- `omrade_stats` columns defined in Task 1 Step 1, seeded in Task 2 Step 1, queried in Task 2 Step 4 — consistent.
- Template variables `rows`, `sort`, `global_min`, `global_max` passed from route in Task 3 Step 3, used in template Task 3 Step 5 — consistent.
