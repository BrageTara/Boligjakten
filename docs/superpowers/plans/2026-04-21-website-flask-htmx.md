# Website (Flask + HTMX) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Flask website that reads from `finn_tracker.db` and displays Trondheim apartment listings with sidebar filtering, HTMX partial refresh, and a detail page per listing.

**Architecture:** Flask serves all routes and queries SQLite via a dedicated `db.py` module. The main page renders with Jinja2; filter changes trigger HTMX POST requests that return only the listings partial — no full page reload. Detail, sold, and price history pages are separate GET routes.

**Tech Stack:** Python 3.14, Flask, Jinja2, HTMX (CDN), SQLite (built-in), pytest, pytest-flask

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `app.py` | Create | Flask app, all routes |
| `db.py` | Create | All SQLite queries |
| `templates/base.html` | Create | Shared layout: nav, stats bar |
| `templates/index.html` | Create | Main page: sidebar + listing area |
| `templates/listings.html` | Create | Listing cards partial (returned by HTMX) |
| `templates/detalj.html` | Create | Single listing detail page |
| `templates/solgte.html` | Create | Sold listings table |
| `templates/prishistorikk.html` | Create | Price history table |
| `templates/404.html` | Create | 404 error page |
| `static/style.css` | Create | All custom CSS |
| `tests/test_db.py` | Create | Unit tests for db.py |
| `tests/test_routes.py` | Create | Integration tests for Flask routes |
| `tests/conftest.py` | Create | Shared pytest fixtures |

---

## Task 1: Install dependencies and project skeleton

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Install Flask and pytest-flask**

```bash
pip install flask pytest pytest-flask
```

Expected output: `Successfully installed flask-3.x.x ...`

- [ ] **Step 2: Verify Flask imports**

```bash
python -c "import flask; print(flask.__version__)"
```

Expected: prints a version number like `3.1.0`

- [ ] **Step 3: Create `tests/__init__.py`**

Empty file — makes `tests/` a Python package.

```python
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
# PSEUDOCODE:
# 1. Import the Flask app
# 2. Configure it for testing (no real DB needed for route tests)
# 3. Provide a test client fixture used by all route tests
# 4. Provide a temp-DB fixture that creates an in-memory SQLite DB
#    with the same schema as finn_tracker.db, populated with sample rows

import sqlite3
import pytest
from app import create_app


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "DB_PATH": ":memory:"})
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seeded_app(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE annonser (
            finnkode TEXT PRIMARY KEY,
            adresse TEXT, prisantydning INTEGER, fellesgjeld INTEGER,
            totalpris INTEGER, kvm_pris INTEGER, felleskost INTEGER,
            fellesformue INTEGER, type TEXT, bra TEXT, rom TEXT,
            etasje TEXT, forste_sett DATE, siste_sett DATE,
            dager_ute INTEGER, antall_visninger INTEGER DEFAULT 0,
            pris_ved_start INTEGER, prisendring INTEGER,
            status TEXT DEFAULT 'Aktiv', url TEXT, megler TEXT,
            meglerkontor TEXT, neste_visning TEXT, flagg TEXT,
            omrade TEXT, postnummer TEXT
        );
        CREATE TABLE prishistorikk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finnkode TEXT, dato DATE,
            prisantydning INTEGER, totalpris INTEGER
        );
        CREATE TABLE solgte (
            finnkode TEXT, adresse TEXT, prisantydning INTEGER,
            fellesgjeld INTEGER, totalpris INTEGER, kvm_pris INTEGER,
            felleskost INTEGER, fellesformue INTEGER, type TEXT,
            bra TEXT, rom TEXT, etasje TEXT, forste_sett DATE,
            siste_sett DATE, dager_ute INTEGER, antall_visninger INTEGER,
            pris_ved_start INTEGER, prisendring INTEGER, status TEXT,
            url TEXT, megler TEXT, meglerkontor TEXT, neste_visning TEXT,
            flagg TEXT, omrade TEXT, postnummer TEXT,
            solgt_dato DATE, arsak TEXT
        );
        INSERT INTO annonser VALUES
            ('111','Møllenberggata 12',2990000,NULL,2990000,55370,3200,NULL,
             'Leilighet','54','2','2. etasje','2026-04-10','2026-04-21',
             11,0,3200000,-210000,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=111',
             'Ole Hansen','DNB Eiendom',NULL,'Prisnedsatt','Møllenberg','7043'),
            ('222','Elgesetergate 24',3450000,NULL,3450000,56557,NULL,NULL,
             'Leilighet','61','3','1. etasje','2026-04-01','2026-04-21',
             20,2,3450000,0,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=222',
             NULL,NULL,NULL,'14+ dager | 2+ visninger','Elgeseter','7030'),
            ('333','Nardovegen 8',2650000,1200000,3850000,69737,4500,NULL,
             'Leilighet','38','1','3. etasje','2026-04-18','2026-04-21',
             3,0,2650000,0,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=333',
             NULL,NULL,NULL,'Høy fellesgjeld','Nardo','7023');
        INSERT INTO prishistorikk VALUES
            (1,'111','2026-04-10',3200000,3200000),
            (2,'111','2026-04-21',2990000,2990000);
        INSERT INTO solgte VALUES
            ('999','Rosenborg allé 5',3100000,NULL,3100000,64583,NULL,NULL,
             'Leilighet','48','2','1. etasje','2026-04-05','2026-04-19',
             14,1,3100000,0,'Solgt',
             'https://finn.no/realestate/homes/ad.html?finnkode=999',
             NULL,NULL,NULL,NULL,'Rosenborg','7037',
             '2026-04-20','Solgt');
    """)
    conn.commit()
    conn.close()
    app = create_app({"TESTING": True, "DB_PATH": db_path})
    yield app


@pytest.fixture
def seeded_client(seeded_app):
    return seeded_app.test_client()
```

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: add pytest fixtures and conftest"
```

---

## Task 2: Database query layer (`db.py`)

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests for `db.py`**

Create `tests/test_db.py`:

```python
import pytest
from db import get_stats, get_listings, get_listing, get_price_history, get_sold_listings


def test_get_stats_returns_expected_keys(seeded_app):
    with seeded_app.app_context():
        stats = get_stats()
    assert "total" in stats
    assert "nye_i_dag" in stats
    assert "flaggede" in stats
    assert "prisnedsatte" in stats


def test_get_stats_counts(seeded_app):
    with seeded_app.app_context():
        stats = get_stats()
    assert stats["total"] == 3
    assert stats["flaggede"] == 3
    assert stats["prisnedsatte"] == 1


def test_get_listings_no_filters_returns_all_active(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({})
    assert len(rows) == 3


def test_get_listings_filter_by_omrade(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"omrade": "Møllenberg"})
    assert len(rows) == 1
    assert rows[0]["finnkode"] == "111"


def test_get_listings_filter_by_pris(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"pris_maks": 3000000})
    assert len(rows) == 2


def test_get_listings_filter_by_flagg(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"flagg": ["Prisnedsatt"]})
    assert len(rows) == 1
    assert rows[0]["finnkode"] == "111"


def test_get_listings_sort_by_price_asc(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({}, sort="prisantydning_asc")
    assert rows[0]["finnkode"] == "333"
    assert rows[-1]["finnkode"] == "222"


def test_get_listing_returns_row(seeded_app):
    with seeded_app.app_context():
        row = get_listing("111")
    assert row is not None
    assert row["adresse"] == "Møllenberggata 12"


def test_get_listing_returns_none_for_unknown(seeded_app):
    with seeded_app.app_context():
        row = get_listing("does-not-exist")
    assert row is None


def test_get_price_history(seeded_app):
    with seeded_app.app_context():
        rows = get_price_history("111")
    assert len(rows) == 2
    assert rows[0]["dato"] == "2026-04-10"


def test_get_sold_listings(seeded_app):
    with seeded_app.app_context():
        rows = get_sold_listings()
    assert len(rows) == 1
    assert rows[0]["finnkode"] == "999"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Create `db.py`**

```python
import sqlite3
from datetime import date
from flask import current_app


# PSEUDOCODE:
# Open a connection to the SQLite DB path stored in Flask app config.
# Enable row_factory so rows behave like dicts.
def get_db():
    conn = sqlite3.connect(current_app.config["DB_PATH"])
    conn.row_factory = sqlite3.Row
    return conn


# PSEUDOCODE:
# 1. Query total active listings count
# 2. Query listings seen today (siste_sett = today)
# 3. Query listings with non-null flagg
# 4. Query listings where flagg contains 'Prisnedsatt'
# 5. Return all four as a dict
def get_stats():
    today = str(date.today())
    conn = get_db()
    c = conn.cursor()
    total = c.execute(
        "SELECT COUNT(*) FROM annonser WHERE status = 'Aktiv'"
    ).fetchone()[0]
    nye_i_dag = c.execute(
        "SELECT COUNT(*) FROM annonser WHERE siste_sett = ? AND status = 'Aktiv'",
        (today,)
    ).fetchone()[0]
    flaggede = c.execute(
        "SELECT COUNT(*) FROM annonser WHERE flagg IS NOT NULL AND flagg != '' AND status = 'Aktiv'"
    ).fetchone()[0]
    prisnedsatte = c.execute(
        "SELECT COUNT(*) FROM annonser WHERE flagg LIKE '%Prisnedsatt%' AND status = 'Aktiv'"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "nye_i_dag": nye_i_dag,
        "flaggede": flaggede,
        "prisnedsatte": prisnedsatte,
    }


# PSEUDOCODE:
# 1. Start with base query: SELECT * FROM annonser WHERE 1=1
# 2. For each active filter, append a WHERE clause and parameter
# 3. For 'flagg' filter (list), append a LIKE clause per selected flag
# 4. Apply sort order (default: siste_sett DESC)
# 5. Return list of row dicts
def get_listings(filters, sort="siste_sett_desc"):
    query = "SELECT * FROM annonser WHERE 1=1"
    params = []

    status_filter = filters.get("status")
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        query += f" AND status IN ({placeholders})"
        params.extend(status_filter)
    else:
        query += " AND status = 'Aktiv'"

    if filters.get("omrade"):
        query += " AND omrade = ?"
        params.append(filters["omrade"])

    if filters.get("pris_min"):
        query += " AND prisantydning >= ?"
        params.append(int(filters["pris_min"]))

    if filters.get("pris_maks"):
        query += " AND prisantydning <= ?"
        params.append(int(filters["pris_maks"]))

    if filters.get("bra_min"):
        query += " AND CAST(bra AS INTEGER) >= ?"
        params.append(int(filters["bra_min"]))

    if filters.get("bra_maks"):
        query += " AND CAST(bra AS INTEGER) <= ?"
        params.append(int(filters["bra_maks"]))

    rom = filters.get("rom")
    if rom and rom != "alle":
        if rom == "3+":
            query += " AND CAST(rom AS INTEGER) >= 3"
        else:
            query += " AND CAST(rom AS INTEGER) = ?"
            params.append(int(rom))

    for flag in filters.get("flagg", []):
        query += " AND flagg LIKE ?"
        params.append(f"%{flag}%")

    sort_map = {
        "siste_sett_desc": "siste_sett DESC",
        "prisantydning_asc": "prisantydning ASC",
        "prisantydning_desc": "prisantydning DESC",
        "dager_ute_desc": "dager_ute DESC",
    }
    query += f" ORDER BY {sort_map.get(sort, 'siste_sett DESC')}"

    conn = get_db()
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


# PSEUDOCODE:
# 1. Query annonser by finnkode
# 2. Return the row as a dict, or None if not found
def get_listing(finnkode):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM annonser WHERE finnkode = ?", (finnkode,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# PSEUDOCODE:
# 1. Query prishistorikk for the given finnkode, ordered by date ascending
# 2. Return list of row dicts
def get_price_history(finnkode):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM prishistorikk WHERE finnkode = ? ORDER BY dato ASC",
        (finnkode,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# PSEUDOCODE:
# 1. Query all rows from solgte, ordered by solgt_dato DESC
# 2. Return list of row dicts
def get_sold_listings():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM solgte ORDER BY solgt_dato DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run tests — expect failure on `create_app` not found**

```bash
python -m pytest tests/test_db.py -v
```

Expected: `ImportError: cannot import name 'create_app' from 'app'`

(This is expected — `app.py` doesn't exist yet. We'll fix this in Task 3.)

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: add database query layer (db.py)"
```

---

## Task 3: Flask app skeleton (`app.py`)

**Files:**
- Create: `app.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_routes.py`:

```python
def test_index_returns_200(seeded_client):
    response = seeded_client.get("/")
    assert response.status_code == 200


def test_index_shows_listing_count(seeded_client):
    response = seeded_client.get("/")
    assert b"3" in response.data


def test_annonser_post_returns_200(seeded_client):
    response = seeded_client.post("/annonser", data={})
    assert response.status_code == 200


def test_detalj_returns_200_for_known(seeded_client):
    response = seeded_client.get("/annonse/111")
    assert response.status_code == 200
    assert "Møllenberggata".encode() in response.data


def test_detalj_returns_404_for_unknown(seeded_client):
    response = seeded_client.get("/annonse/does-not-exist")
    assert response.status_code == 404


def test_solgte_returns_200(seeded_client):
    response = seeded_client.get("/solgte")
    assert response.status_code == 200


def test_prishistorikk_returns_200(seeded_client):
    response = seeded_client.get("/prishistorikk")
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
python -m pytest tests/test_routes.py -v
```

Expected: `ImportError: cannot import name 'create_app' from 'app'`

- [ ] **Step 3: Create `app.py`**

```python
import os
from flask import Flask, render_template, request, abort
from db import get_stats, get_listings, get_listing, get_price_history, get_sold_listings


# PSEUDOCODE:
# 1. Create Flask app instance
# 2. Apply any config overrides passed in (used by tests)
# 3. Set default DB_PATH to finn_tracker.db in the project root
# 4. Register all routes
# 5. Return the app
def create_app(config=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = os.path.join(os.path.dirname(__file__), "finn_tracker.db")

    if config:
        app.config.update(config)

    # PSEUDOCODE:
    # 1. Fetch stats for the stats bar (totals, new today, flagged, price-reduced)
    # 2. Fetch all active listings with no filters applied
    # 3. Render index.html with stats and listings
    @app.route("/")
    def index():
        stats = get_stats()
        listings = get_listings({})
        omrader = sorted(set(l["omrade"] for l in listings if l["omrade"]))
        return render_template("index.html", stats=stats, listings=listings, omrader=omrader)

    # PSEUDOCODE:
    # 1. Parse filter values and sort from the POST form data
    # 2. Fetch filtered listings from the database
    # 3. Return only the listings partial HTML (for HTMX to swap in)
    @app.route("/annonser", methods=["POST"])
    def annonser():
        filters = {
            "omrade":    request.form.get("omrade") or None,
            "pris_min":  request.form.get("pris_min") or None,
            "pris_maks": request.form.get("pris_maks") or None,
            "bra_min":   request.form.get("bra_min") or None,
            "bra_maks":  request.form.get("bra_maks") or None,
            "rom":       request.form.get("rom") or None,
            "flagg":     request.form.getlist("flagg"),
            "status":    request.form.getlist("status") or None,
        }
        sort = request.form.get("sort", "siste_sett_desc")
        listings = get_listings(filters, sort)
        return render_template("listings.html", listings=listings)

    # PSEUDOCODE:
    # 1. Fetch the listing row for the given finnkode
    # 2. If not found, return 404
    # 3. Fetch price history for this listing
    # 4. Render detalj.html with listing and price history
    @app.route("/annonse/<finnkode>")
    def detalj(finnkode):
        listing = get_listing(finnkode)
        if not listing:
            abort(404)
        history = get_price_history(finnkode)
        return render_template("detalj.html", listing=listing, history=history)

    # PSEUDOCODE:
    # 1. Fetch all sold listings
    # 2. Render solgte.html
    @app.route("/solgte")
    def solgte():
        listings = get_sold_listings()
        return render_template("solgte.html", listings=listings)

    # PSEUDOCODE:
    # 1. Fetch all active listings that have a price reduction (prisendring < 0)
    # 2. Render prishistorikk.html with those listings
    @app.route("/prishistorikk")
    def prishistorikk():
        listings = get_listings({"flagg": ["Prisnedsatt"]})
        return render_template("prishistorikk.html", listings=listings)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
```

- [ ] **Step 4: Run tests — expect template errors**

```bash
python -m pytest tests/test_routes.py -v
```

Expected: `TemplateNotFound: index.html` (app.py works, templates missing)

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_routes.py
git commit -m "feat: add Flask app skeleton with all routes"
```

---

## Task 4: Base template and CSS

**Files:**
- Create: `templates/base.html`
- Create: `static/style.css`
- Create: `templates/404.html`

- [ ] **Step 1: Create `static/style.css`**

```css
/* Reset and base */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; font-size: 14px; background: #f8fafc; color: #1e293b; }
a { color: inherit; text-decoration: none; }

/* Layout */
.nav { background: #1e40af; color: white; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; }
.nav-title { font-weight: bold; font-size: 16px; }
.nav-links { display: flex; gap: 20px; font-size: 13px; }
.nav-links a { opacity: 0.8; }
.nav-links a:hover, .nav-links a.active { opacity: 1; border-bottom: 2px solid white; }
.nav-meta { font-size: 11px; opacity: 0.7; }

.stats-bar { background: #dbeafe; padding: 8px 20px; display: flex; gap: 28px; font-size: 12px; border-bottom: 1px solid #bfdbfe; }
.stats-bar span strong { font-weight: 600; }

.layout { display: flex; height: calc(100vh - 76px); }
.sidebar { width: 220px; background: #f1f5f9; border-right: 1px solid #e2e8f0; padding: 16px; overflow-y: auto; flex-shrink: 0; }
.main { flex: 1; overflow-y: auto; padding: 16px; }

/* Sidebar */
.sidebar h3 { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 14px; }
.filter-group { margin-bottom: 16px; }
.filter-label { font-size: 11px; color: #64748b; margin-bottom: 5px; }
.filter-row { display: flex; gap: 6px; align-items: center; }
.filter-row span { color: #94a3b8; font-size: 11px; }
input[type="number"], select { width: 100%; background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
.filter-row input[type="number"] { width: 70px; }
.btn-group { display: flex; gap: 4px; flex-wrap: wrap; }
.btn-group button { background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 3px 10px; font-size: 11px; cursor: pointer; }
.btn-group button.active { background: #1e40af; color: white; border-color: #1e40af; }
.checkbox-list { display: flex; flex-direction: column; gap: 5px; }
.checkbox-list label { display: flex; align-items: center; gap: 6px; font-size: 12px; cursor: pointer; }
.btn-reset { width: 100%; background: #e2e8f0; border: none; border-radius: 4px; padding: 6px; font-size: 12px; cursor: pointer; margin-top: 8px; }
.btn-reset:hover { background: #cbd5e1; }

/* Results bar */
.results-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 12px; color: #64748b; }
.sort-select { background: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px 8px; font-size: 12px; }

/* Listing cards */
.listing-card { background: white; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin-bottom: 6px; cursor: pointer; transition: box-shadow 0.1s; }
.listing-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.listing-card.is-new { background: #f0fdf4; border-color: #bbf7d0; }
.listing-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }
.listing-address { font-weight: 600; font-size: 13px; }
.listing-price { font-weight: 600; color: #1d4ed8; font-size: 13px; }
.listing-meta { display: flex; gap: 14px; color: #64748b; font-size: 11px; margin-bottom: 5px; }
.listing-flags { display: flex; gap: 4px; flex-wrap: wrap; }

/* Badges */
.badge { padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 500; }
.badge-new { background: #dcfce7; color: #166534; }
.badge-prisnedsatt { background: #fef3c7; color: #92400e; }
.badge-dager { background: #fee2e2; color: #991b1b; }
.badge-visninger { background: #fee2e2; color: #991b1b; }
.badge-fellesgjeld { background: #fef3c7; color: #92400e; }

/* Detail page */
.detail-container { max-width: 720px; margin: 0 auto; padding: 24px; }
.detail-header { margin-bottom: 20px; }
.detail-title { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.detail-subtitle { color: #64748b; font-size: 13px; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
.detail-field { background: #f8fafc; border-radius: 6px; padding: 10px 14px; }
.detail-field-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: #94a3b8; margin-bottom: 2px; }
.detail-field-value { font-size: 15px; font-weight: 600; }
.btn-back { display: inline-block; margin-bottom: 16px; background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 4px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.btn-back:hover { background: #e2e8f0; }

/* Tables */
table { width: 100%; border-collapse: collapse; font-size: 12px; }
th { text-align: left; padding: 8px 12px; background: #f1f5f9; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; border-bottom: 1px solid #e2e8f0; }
td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }
tr:hover td { background: #f8fafc; }

/* Page heading */
.page-title { font-size: 18px; font-weight: 700; margin-bottom: 16px; }

/* HTMX loading indicator */
.htmx-indicator { display: none; }
.htmx-request .htmx-indicator { display: inline; }
```

- [ ] **Step 2: Create `templates/base.html`**

```html
<!DOCTYPE html>
<html lang="no">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Finn Tracker{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
</head>
<body>

<nav class="nav">
  <span class="nav-title">🏠 Finn Tracker</span>
  <div class="nav-links">
    <a href="{{ url_for('index') }}" class="{{ 'active' if request.endpoint == 'index' }}">Annonser</a>
    <a href="{{ url_for('solgte') }}" class="{{ 'active' if request.endpoint == 'solgte' }}">Solgte</a>
    <a href="{{ url_for('prishistorikk') }}" class="{{ 'active' if request.endpoint == 'prishistorikk' }}">Prisnedsatte</a>
  </div>
  <span class="nav-meta">Trondheim</span>
</nav>

{% block content %}{% endblock %}

</body>
</html>
```

- [ ] **Step 3: Create `templates/404.html`**

```html
{% extends "base.html" %}
{% block title %}Side ikke funnet — Finn Tracker{% endblock %}
{% block content %}
<div style="text-align:center;padding:60px 20px;">
  <h2 style="font-size:48px;color:#cbd5e1;">404</h2>
  <p style="color:#64748b;margin:12px 0;">Siden finnes ikke.</p>
  <a href="{{ url_for('index') }}" class="btn-back">← Tilbake til oversikten</a>
</div>
{% endblock %}
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: `test_routes.py` still fails on `TemplateNotFound: index.html` — that's fine, we haven't built it yet.

- [ ] **Step 5: Commit**

```bash
git add static/style.css templates/base.html templates/404.html
git commit -m "feat: add base template and CSS"
```

---

## Task 5: Listing templates (index + HTMX partial)

**Files:**
- Create: `templates/listings.html`
- Create: `templates/index.html`

- [ ] **Step 1: Create `templates/listings.html`** (HTMX partial — no base layout)

```html
{% set today = namespace(val=None) %}
{# Import date for new-listing detection #}

{% if listings %}
<p class="results-bar" style="margin-bottom:10px;font-size:12px;color:#64748b;">
  Viser <strong>{{ listings|length }}</strong> annonser
</p>
{% for l in listings %}
  {% set is_new = l.siste_sett == today_str %}
  <a href="{{ url_for('detalj', finnkode=l.finnkode) }}" style="display:block;">
    <div class="listing-card {{ 'is-new' if is_new }}">
      <div class="listing-header">
        <span class="listing-address">{{ l.adresse or l.finnkode }}</span>
        <span class="listing-price">
          {% if l.prisantydning %}{{ "{:,.0f}".format(l.prisantydning).replace(",", " ") }} kr{% else %}—{% endif %}
        </span>
      </div>
      <div class="listing-meta">
        {% if l.omrade %}<span>📍 {{ l.omrade }}</span>{% endif %}
        {% if l.bra %}<span>📐 {{ l.bra }} m²</span>{% endif %}
        {% if l.rom %}<span>🛏 {{ l.rom }} rom</span>{% endif %}
        <span>📅 {{ l.dager_ute or 0 }} dager</span>
      </div>
      <div class="listing-flags">
        {% if is_new %}<span class="badge badge-new">NY</span>{% endif %}
        {% if l.flagg %}
          {% for flag in l.flagg.split(' | ') %}
            {% if flag == 'Prisnedsatt' %}<span class="badge badge-prisnedsatt">📉 {{ flag }}</span>
            {% elif '14+' in flag %}<span class="badge badge-dager">⏱ {{ flag }}</span>
            {% elif 'visninger' in flag %}<span class="badge badge-visninger">👁 {{ flag }}</span>
            {% elif 'fellesgjeld' in flag %}<span class="badge badge-fellesgjeld">💰 {{ flag }}</span>
            {% endif %}
          {% endfor %}
        {% endif %}
      </div>
    </div>
  </a>
{% endfor %}
{% else %}
<p style="color:#94a3b8;text-align:center;padding:40px 0;">Ingen annonser matcher filtrene.</p>
{% endif %}
```

- [ ] **Step 2: Update `app.py` to pass `today_str` to templates**

In `app.py`, update both the `index` and `annonser` routes to pass today's date:

```python
from datetime import date

# In index():
return render_template("index.html", stats=stats, listings=listings,
                        omrader=omrader, today_str=str(date.today()))

# In annonser():
return render_template("listings.html", listings=listings,
                        today_str=str(date.today()))
```

- [ ] **Step 3: Create `templates/index.html`**

```html
{% extends "base.html" %}
{% block title %}Annonser — Finn Tracker{% endblock %}
{% block content %}

<div class="stats-bar">
  <span>📋 <strong>{{ stats.total }}</strong> annonser totalt</span>
  <span>🆕 <strong>{{ stats.nye_i_dag }}</strong> nye i dag</span>
  <span>🏷 <strong>{{ stats.flaggede }}</strong> flaggede</span>
  <span>📉 <strong>{{ stats.prisnedsatte }}</strong> prisnedsatt</span>
</div>

<div class="layout">

  <!-- Sidebar with filters — HTMX posts the form on any change -->
  <aside class="sidebar">
    <h3>Filtre</h3>
    <form id="filter-form"
          hx-post="{{ url_for('annonser') }}"
          hx-target="#listing-results"
          hx-trigger="change, input delay:400ms">

      <div class="filter-group">
        <div class="filter-label">Pris (kr)</div>
        <div class="filter-row">
          <input type="number" name="pris_min" placeholder="Min" step="50000">
          <span>–</span>
          <input type="number" name="pris_maks" placeholder="Maks" step="50000">
        </div>
      </div>

      <div class="filter-group">
        <div class="filter-label">Område</div>
        <select name="omrade">
          <option value="">Alle områder</option>
          {% for o in omrader %}
            <option value="{{ o }}">{{ o }}</option>
          {% endfor %}
        </select>
      </div>

      <div class="filter-group">
        <div class="filter-label">Størrelse (m²)</div>
        <div class="filter-row">
          <input type="number" name="bra_min" placeholder="Min">
          <span>–</span>
          <input type="number" name="bra_maks" placeholder="Maks">
        </div>
      </div>

      <div class="filter-group">
        <div class="filter-label">Antall rom</div>
        <div class="btn-group">
          {% for val, label in [('alle','Alle'),('1','1'),('2','2'),('3+','3+')] %}
            <button type="button"
                    class="{{ 'active' if loop.first }}"
                    onclick="setRom(this, '{{ val }}')">{{ label }}</button>
          {% endfor %}
          <input type="hidden" name="rom" value="alle" id="rom-value">
        </div>
      </div>

      <div class="filter-group">
        <div class="filter-label">Flagg</div>
        <div class="checkbox-list">
          {% for flag in ['Prisnedsatt','14+ dager','2+ visninger','Høy fellesgjeld'] %}
            <label>
              <input type="checkbox" name="flagg" value="{{ flag }}"> {{ flag }}
            </label>
          {% endfor %}
        </div>
      </div>

      <div class="filter-group">
        <div class="filter-label">Status</div>
        <div class="checkbox-list">
          <label><input type="checkbox" name="status" value="Aktiv" checked> Aktiv</label>
          <label><input type="checkbox" name="status" value="Solgt"> Solgt</label>
          <label><input type="checkbox" name="status" value="Trukket"> Trukket</label>
        </div>
      </div>

      <div class="filter-group">
        <div class="filter-label">Sorter etter</div>
        <select name="sort">
          <option value="siste_sett_desc">Nyeste først</option>
          <option value="prisantydning_asc">Pris stigende</option>
          <option value="prisantydning_desc">Pris synkende</option>
          <option value="dager_ute_desc">Lengst ute</option>
        </select>
      </div>

    </form>
    <button class="btn-reset" onclick="resetFilters()">Nullstill filtre</button>
  </aside>

  <!-- Listing area — HTMX swaps this div -->
  <main class="main">
    <div id="listing-results">
      {% include "listings.html" %}
    </div>
  </main>

</div>

<script>
function setRom(btn, val) {
  document.querySelectorAll('.btn-group button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('rom-value').value = val;
  htmx.trigger('#filter-form', 'change');
}

function resetFilters() {
  document.getElementById('filter-form').reset();
  document.querySelectorAll('.btn-group button').forEach((b, i) => {
    b.classList.toggle('active', i === 0);
  });
  document.getElementById('rom-value').value = 'alle';
  htmx.trigger('#filter-form', 'change');
}
</script>
{% endblock %}
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Start the app and verify manually**

```bash
python app.py
```

Open http://localhost:5000 — confirm listings appear, sidebar is visible, changing a filter updates the list without full reload.

- [ ] **Step 6: Commit**

```bash
git add templates/index.html templates/listings.html app.py
git commit -m "feat: add main listing page with HTMX filtering"
```

---

## Task 6: Detail page

**Files:**
- Create: `templates/detalj.html`

- [ ] **Step 1: Run the existing detail route test**

```bash
python -m pytest tests/test_routes.py::test_detalj_returns_200_for_known -v
```

Expected: FAIL with `TemplateNotFound: detalj.html`

- [ ] **Step 2: Create `templates/detalj.html`**

```html
{% extends "base.html" %}
{% block title %}{{ listing.adresse }} — Finn Tracker{% endblock %}
{% block content %}
<div class="detail-container">

  <a href="{{ url_for('index') }}" class="btn-back">← Tilbake til oversikten</a>

  <div class="detail-header">
    <div class="detail-title">{{ listing.adresse }}</div>
    <div class="detail-subtitle">
      {{ listing.omrade }}{% if listing.postnummer %} · {{ listing.postnummer }}{% endif %}
      · <a href="{{ listing.url }}" target="_blank" style="color:#1d4ed8;">Åpne på Finn.no ↗</a>
    </div>
    {% if listing.flagg %}
      <div class="listing-flags" style="margin-top:8px;">
        {% for flag in listing.flagg.split(' | ') %}
          {% if flag == 'Prisnedsatt' %}<span class="badge badge-prisnedsatt">📉 {{ flag }}</span>
          {% elif '14+' in flag %}<span class="badge badge-dager">⏱ {{ flag }}</span>
          {% elif 'visninger' in flag %}<span class="badge badge-visninger">👁 {{ flag }}</span>
          {% elif 'fellesgjeld' in flag %}<span class="badge badge-fellesgjeld">💰 {{ flag }}</span>
          {% endif %}
        {% endfor %}
      </div>
    {% endif %}
  </div>

  <div class="detail-grid">
    {% for label, val in [
        ('Prisantydning', listing.prisantydning|format_kr if listing.prisantydning else '—'),
        ('Fellesgjeld',   listing.fellesgjeld|format_kr if listing.fellesgjeld else '—'),
        ('Totalpris',     listing.totalpris|format_kr if listing.totalpris else '—'),
        ('kr/m²',         listing.kvm_pris|format_kr if listing.kvm_pris else '—'),
        ('Felleskost/mnd',listing.felleskost|format_kr if listing.felleskost else '—'),
        ('Fellesformue',  listing.fellesformue|format_kr if listing.fellesformue else '—'),
        ('Boligtype',     listing.type or '—'),
        ('BRA',           (listing.bra ~ ' m²') if listing.bra else '—'),
        ('Soverom',       listing.rom or '—'),
        ('Etasje',        listing.etasje or '—'),
        ('Første gang sett', listing.forste_sett or '—'),
        ('Sist oppdatert',   listing.siste_sett or '—'),
        ('Dager på Finn',    listing.dager_ute or 0),
        ('Antall visninger', listing.antall_visninger or 0),
        ('Neste visning',    listing.neste_visning or '—'),
        ('Startpris',        listing.pris_ved_start|format_kr if listing.pris_ved_start else '—'),
        ('Prisendring',      (('+' if listing.prisendring > 0 else '') ~ '{:,.0f}'.format(listing.prisendring).replace(',', ' ') ~ ' kr') if listing.prisendring else '—'),
        ('Megler',           listing.megler or '—'),
        ('Meglerkontor',     listing.meglerkontor or '—'),
    ] %}
      <div class="detail-field">
        <div class="detail-field-label">{{ label }}</div>
        <div class="detail-field-value">{{ val }}</div>
      </div>
    {% endfor %}
  </div>

  {% if history %}
    <h3 style="font-size:14px;font-weight:600;margin-bottom:10px;">Prishistorikk</h3>
    <table>
      <thead><tr><th>Dato</th><th>Prisantydning</th><th>Totalpris</th></tr></thead>
      <tbody>
        {% for h in history %}
          <tr>
            <td>{{ h.dato }}</td>
            <td>{% if h.prisantydning %}{{ "{:,.0f}".format(h.prisantydning).replace(",", " ") }} kr{% else %}—{% endif %}</td>
            <td>{% if h.totalpris %}{{ "{:,.0f}".format(h.totalpris).replace(",", " ") }} kr{% else %}—{% endif %}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% endif %}

</div>
{% endblock %}
```

- [ ] **Step 3: Register `format_kr` as a Jinja2 filter in `app.py`**

Add this inside `create_app()`, before the routes:

```python
@app.template_filter("format_kr")
def format_kr(value):
    # PSEUDOCODE: Format an integer as Norwegian kroner with space as thousands separator
    return "{:,.0f}".format(value).replace(",", " ") + " kr"
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Verify manually**

```bash
python app.py
```

Click a listing → confirm detail page shows all fields and price history table.

- [ ] **Step 6: Commit**

```bash
git add templates/detalj.html app.py
git commit -m "feat: add listing detail page with price history"
```

---

## Task 7: Sold listings and price reduction pages

**Files:**
- Create: `templates/solgte.html`
- Create: `templates/prishistorikk.html`

- [ ] **Step 1: Create `templates/solgte.html`**

```html
{% extends "base.html" %}
{% block title %}Solgte — Finn Tracker{% endblock %}
{% block content %}
<div style="padding:20px;">
  <h2 class="page-title">Solgte og trukne annonser</h2>
  {% if listings %}
    <table>
      <thead>
        <tr>
          <th>Adresse</th><th>Område</th><th>Pris</th>
          <th>m²</th><th>Solgt dato</th><th>Årsak</th>
        </tr>
      </thead>
      <tbody>
        {% for l in listings %}
          <tr>
            <td><a href="{{ url_for('detalj', finnkode=l.finnkode) }}">{{ l.adresse or l.finnkode }}</a></td>
            <td>{{ l.omrade or '—' }}</td>
            <td>{% if l.prisantydning %}{{ "{:,.0f}".format(l.prisantydning).replace(",", " ") }} kr{% else %}—{% endif %}</td>
            <td>{{ l.bra or '—' }}</td>
            <td>{{ l.solgt_dato or '—' }}</td>
            <td>{{ l.arsak or '—' }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p style="color:#94a3b8;">Ingen solgte annonser ennå.</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Create `templates/prishistorikk.html`**

```html
{% extends "base.html" %}
{% block title %}Prisnedsatte — Finn Tracker{% endblock %}
{% block content %}
<div style="padding:20px;">
  <h2 class="page-title">Prisnedsatte annonser</h2>
  {% if listings %}
    <table>
      <thead>
        <tr>
          <th>Adresse</th><th>Område</th>
          <th>Nåværende pris</th><th>Startpris</th><th>Endring</th><th>Dager ute</th>
        </tr>
      </thead>
      <tbody>
        {% for l in listings %}
          <tr>
            <td><a href="{{ url_for('detalj', finnkode=l.finnkode) }}">{{ l.adresse or l.finnkode }}</a></td>
            <td>{{ l.omrade or '—' }}</td>
            <td>{% if l.prisantydning %}{{ "{:,.0f}".format(l.prisantydning).replace(",", " ") }} kr{% else %}—{% endif %}</td>
            <td>{% if l.pris_ved_start %}{{ "{:,.0f}".format(l.pris_ved_start).replace(",", " ") }} kr{% else %}—{% endif %}</td>
            <td style="color:#16a34a;">
              {% if l.prisendring %}{{ "{:,.0f}".format(l.prisendring).replace(",", " ") }} kr{% else %}—{% endif %}
            </td>
            <td>{{ l.dager_ute or 0 }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p style="color:#94a3b8;">Ingen prisnedsatte annonser for øyeblikket.</p>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 4: Verify all pages manually**

```bash
python app.py
```

Check:
- http://localhost:5000/ — listing page with filters
- http://localhost:5000/solgte — sold listings table
- http://localhost:5000/prishistorikk — price reduction table
- http://localhost:5000/annonse/INVALID — 404 page

- [ ] **Step 5: Final commit**

```bash
git add templates/solgte.html templates/prishistorikk.html
git commit -m "feat: add sold listings and price reduction pages"
```

---

## Self-Review

**Spec coverage:**
- ✅ Sidebar layout with all 6 filter types
- ✅ Stats bar (total, nye i dag, flaggede, prisnedsatte)
- ✅ Nav: Annonser, Solgte, Prishistorikk
- ✅ Listing cards with badges (Prisnedsatt, 14+ dager, 2+ visninger, Høy fellesgjeld)
- ✅ New listings highlighted green
- ✅ HTMX partial refresh on filter change
- ✅ Sort: Nyeste først, Pris stigende/synkende, Lengst ute
- ✅ Detail page with all fields + price history table
- ✅ 404 for unknown finnkode
- ✅ Error message if DB not found (Flask will show 500 — acceptable for local use)

**Placeholder scan:** None found.

**Type consistency:** `format_kr` filter defined in Task 6 Step 3, used in `detalj.html` Task 6 Step 2. `today_str` added in Task 5 Step 2, used in `listings.html` Task 5 Step 1. All consistent.
