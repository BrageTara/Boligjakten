# Nybygg-støtte: filter og histogram — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape alle boliger i Trondheim (brukt + nybygg), legg til boligtype-filter med toggle-knapper, og vis nybygg som egne segmenter i histogrammet.

**Architecture:** `er_nybygg` lagres som INTEGER (0/1) i `annonser` og `solgte`. Detekteres fra URL-strukturen til Finn.no (`/newbuildings/` vs `/homes/`). Filteret sendes via eksisterende HTMX-form. Histogrammet utvides med `ny_aktive`/`ny_solgte` per bin, rendret med 4 CSS-segmenter og klikkbar JS-legende.

**Tech Stack:** Python/SQLite, Flask, HTMX, vanilla JS, CSS

---

## Berørte filer

| Fil | Hva endres |
|---|---|
| `scraper.py` | Fjern `is_new_property=false` fra URL, legg `er_nybygg` på listing-dict |
| `finn_tracker_db.py` | DB-migrasjon, `er_nybygg` i upsert + mark_sold, histogram bygger 4 felt per bin |
| `db.py` | `get_listings()` filtrerer på `er_nybygg`; `get_omrade_histogram_cached` returnerer ny_aktive/ny_solgte |
| `app.py` | Henter `er_nybygg`-liste fra POST-data og sender til `get_listings()` |
| `templates/index.html` | To toggle-knapper (Brukt/Nybygg) + JS for å togglehåndtere |
| `templates/omrade_histogram.html` | 4 segmenter per søyle + klikkbar JS-legende |
| `static/style.css` | Farger for lysegrønn og mørkegrønn histogram-segmenter |
| `tests/conftest.py` | `er_nybygg` kolonne i test-skjema og seed-data |
| `tests/test_db.py` | Tester for `er_nybygg`-filter |

---

## Task 1: Oppdater SEARCH_URL og legg til er_nybygg-deteksjon i scraper.py

**Files:**
- Modify: `scraper.py:9-13` (SEARCH_URL)
- Modify: `scraper.py:96-110` (fetch_all_listings — tilordner er_nybygg)

- [ ] **Step 1: Endre SEARCH_URL**

I `scraper.py`, erstatt linjene 9–13 med:

```python
SEARCH_URL = (
    "https://www.finn.no/realestate/homes/search.html"
    "?location=1.20016.20318"
    "&sort=PUBLISHED_DESC"
)
```

- [ ] **Step 2: Legg til er_nybygg i fetch_all_listings**

I `scraper.py`, i løkken som bygger `batch` (ca. linje 101–111), endre til:

```python
        batch = []
        for href in links:
            m = re.search(r"finnkode=(\d+)", href)
            if not m:
                m = re.search(r"/(\d+)(?:\?|$)", href)
            if m:
                finnkode = m.group(1)
                if finnkode not in seen:
                    seen.add(finnkode)
                    er_nybygg = 1 if "/newbuildings/" in href else 0
                    batch.append({"finnkode": finnkode, "url": href, "er_nybygg": er_nybygg})
```

- [ ] **Step 3: Verifiser manuelt**

Åpne Python-konsoll og sjekk at URL-en ikke lenger inneholder `is_new_property`:

```python
from scraper import SEARCH_URL
assert "is_new_property" not in SEARCH_URL
print(SEARCH_URL)
```

Forventet output: URL uten `is_new_property=false`.

- [ ] **Step 4: Commit**

```bash
git add scraper.py
git commit -m "feat: scrape all listings (brukt + nybygg), detect er_nybygg from URL"
```

---

## Task 2: DB-migrasjon og upsert — er_nybygg i finn_tracker_db.py

**Files:**
- Modify: `finn_tracker_db.py:29-58` (CREATE TABLE annonser)
- Modify: `finn_tracker_db.py:83-101` (CREATE TABLE solgte)
- Modify: `finn_tracker_db.py:116-120` (migrasjonsblokk)
- Modify: `finn_tracker_db.py:223-333` (upsert_listing)
- Modify: `finn_tracker_db.py:344-368` (mark_sold)

- [ ] **Step 1: Legg til er_nybygg i CREATE TABLE annonser**

I `finn_tracker_db.py`, legg til `er_nybygg INTEGER DEFAULT 0` etter `postnummer TEXT` i annonser-tabellen:

```python
    c.execute("""
        CREATE TABLE IF NOT EXISTS annonser (
            finnkode        TEXT PRIMARY KEY,
            adresse         TEXT,
            prisantydning   INTEGER,
            fellesgjeld     INTEGER,
            totalpris       INTEGER,
            kvm_pris        INTEGER,
            felleskost      INTEGER,
            fellesformue    INTEGER,
            type            TEXT,
            bra             TEXT,
            rom             TEXT,
            etasje          TEXT,
            forste_sett     DATE,
            siste_sett      DATE,
            dager_ute       INTEGER,
            antall_visninger INTEGER DEFAULT 0,
            pris_ved_start  INTEGER,
            prisendring     INTEGER,
            status          TEXT DEFAULT 'Aktiv',
            url             TEXT,
            megler          TEXT,
            meglerkontor    TEXT,
            neste_visning   TEXT,
            flagg           TEXT,
            omrade          TEXT,
            postnummer      TEXT,
            er_nybygg       INTEGER DEFAULT 0
        )
    """)
```

- [ ] **Step 2: Legg til er_nybygg i CREATE TABLE solgte**

I `finn_tracker_db.py`, legg til `er_nybygg INTEGER DEFAULT 0` etter `postnummer TEXT` i solgte-tabellen:

```python
    c.execute("""
        CREATE TABLE IF NOT EXISTS solgte (
            finnkode        TEXT,
            adresse         TEXT,
            prisantydning   INTEGER,
            fellesgjeld     INTEGER,
            totalpris       INTEGER,
            kvm_pris        INTEGER,
            felleskost      INTEGER,
            fellesformue    INTEGER,
            type            TEXT,
            bra             TEXT,
            rom             TEXT,
            etasje          TEXT,
            forste_sett     DATE,
            siste_sett      DATE,
            dager_ute       INTEGER,
            antall_visninger INTEGER,
            pris_ved_start  INTEGER,
            prisendring     INTEGER,
            status          TEXT,
            url             TEXT,
            megler          TEXT,
            meglerkontor    TEXT,
            neste_visning   TEXT,
            flagg           TEXT,
            omrade          TEXT,
            postnummer      TEXT,
            solgt_dato      DATE,
            arsak           TEXT,
            er_nybygg       INTEGER DEFAULT 0
        )
    """)
```

- [ ] **Step 3: Legg til migrasjon for eksisterende DB**

Etter den eksisterende `histogram_json`-migrasjonsblokken (ca. linje 116–119), legg til:

```python
    # Migration: add er_nybygg if upgrading from older schema
    try:
        c.execute("ALTER TABLE annonser ADD COLUMN er_nybygg INTEGER DEFAULT 0")
    except Exception:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE solgte ADD COLUMN er_nybygg INTEGER DEFAULT 0")
    except Exception:
        pass  # Column already exists
```

- [ ] **Step 4: Oppdater upsert_listing til å lagre er_nybygg**

I `upsert_listing`, legg til `er_nybygg` i INSERT-kolonner, VALUES, ON CONFLICT og params-dict.

Erstatt INSERT-setningen (ca. linje 269–333) med:

```python
    c.execute("""
        INSERT INTO annonser (
            finnkode, adresse, prisantydning, fellesgjeld, totalpris, kvm_pris,
            felleskost, fellesformue, type, bra, rom, etasje,
            forste_sett, siste_sett, dager_ute, antall_visninger,
            pris_ved_start, prisendring, status, url,
            megler, meglerkontor, neste_visning, flagg, omrade, postnummer, er_nybygg
        ) VALUES (
            :finnkode, :adresse, :prisantydning, :fellesgjeld, :totalpris, :kvm_pris,
            :felleskost, :fellesformue, :type, :bra, :rom, :etasje,
            :forste_sett, :siste_sett, :dager_ute, :antall_visninger,
            :pris_ved_start, :prisendring, :status, :url,
            :megler, :meglerkontor, :neste_visning, :flagg, :omrade, :postnummer, :er_nybygg
        )
        ON CONFLICT(finnkode) DO UPDATE SET
            adresse         = excluded.adresse,
            prisantydning   = excluded.prisantydning,
            fellesgjeld     = excluded.fellesgjeld,
            totalpris       = excluded.totalpris,
            kvm_pris        = excluded.kvm_pris,
            felleskost      = excluded.felleskost,
            fellesformue    = excluded.fellesformue,
            type            = excluded.type,
            bra             = excluded.bra,
            rom             = excluded.rom,
            etasje          = excluded.etasje,
            siste_sett      = excluded.siste_sett,
            dager_ute       = excluded.dager_ute,
            antall_visninger = excluded.antall_visninger,
            prisendring     = excluded.prisendring,
            status          = excluded.status,
            megler          = excluded.megler,
            meglerkontor    = excluded.meglerkontor,
            neste_visning   = excluded.neste_visning,
            flagg           = excluded.flagg,
            omrade          = excluded.omrade,
            postnummer      = excluded.postnummer,
            er_nybygg       = excluded.er_nybygg
    """, {
        "finnkode":         finnkode,
        "adresse":          ad.get("adresse"),
        "prisantydning":    ad.get("prisantydning"),
        "fellesgjeld":      ad.get("fellesgjeld"),
        "totalpris":        ad.get("totalpris"),
        "kvm_pris":         kvm_pris,
        "felleskost":       ad.get("felleskost"),
        "fellesformue":     ad.get("fellesformue"),
        "type":             ad.get("type"),
        "bra":              ad.get("bra"),
        "rom":              ad.get("rom"),
        "etasje":           ad.get("etasje"),
        "forste_sett":      str(forste_sett),
        "siste_sett":       str(today),
        "dager_ute":        dager,
        "antall_visninger": antall_visninger,
        "pris_ved_start":   pris_ved_start,
        "prisendring":      prisendring,
        "status":           "Aktiv",
        "url":              f"https://www.finn.no/realestate/homes/ad.html?finnkode={finnkode}",
        "megler":           ad.get("megler"),
        "meglerkontor":     ad.get("meglerkontor"),
        "neste_visning":    ad.get("neste_visning"),
        "flagg":            " | ".join(flagg) if flagg else None,
        "omrade":           ad.get("omrade"),
        "postnummer":       ad.get("postnummer"),
        "er_nybygg":        ad.get("er_nybygg", 0),
    })
```

- [ ] **Step 5: Legg til er_nybygg i mark_sold INSERT**

I `mark_sold`, legg til `er_nybygg` i kolonne- og VALUES-listen:

```python
    c.execute("""
        INSERT INTO solgte (
            finnkode, adresse, prisantydning, fellesgjeld, totalpris, kvm_pris,
            felleskost, fellesformue, type, bra, rom, etasje,
            forste_sett, siste_sett, dager_ute, antall_visninger,
            pris_ved_start, prisendring, status, url,
            megler, meglerkontor, neste_visning, flagg, omrade, postnummer,
            solgt_dato, arsak, er_nybygg
        ) VALUES (
            :finnkode, :adresse, :prisantydning, :fellesgjeld, :totalpris, :kvm_pris,
            :felleskost, :fellesformue, :type, :bra, :rom, :etasje,
            :forste_sett, :siste_sett, :dager_ute, :antall_visninger,
            :pris_ved_start, :prisendring, :status, :url,
            :megler, :meglerkontor, :neste_visning, :flagg, :omrade, :postnummer,
            :solgt_dato, :arsak, :er_nybygg
        )
    """, {**row, "solgt_dato": str(today), "arsak": arsak})
```

- [ ] **Step 6: Legg til er_nybygg i main()-løkken**

I `main()`, der `upsert_listing` kalles (ca. linje 426), pass `er_nybygg` videre via `ad`-dict. Rett over `upsert_listing`-kallet, legg til:

```python
                ad["er_nybygg"] = listing.get("er_nybygg", 0)
```

- [ ] **Step 7: Commit**

```bash
git add finn_tracker_db.py
git commit -m "feat: add er_nybygg column to annonser/solgte, persist boligtype from scraper"
```

---

## Task 3: Oppdater update_omrade_stats til å bygge 4-felts histogram

**Files:**
- Modify: `finn_tracker_db.py:134-210` (update_omrade_stats)

- [ ] **Step 1: Hent er_nybygg fra annonser og solgte**

Erstatt de to `active_rows`/`sold_rows`-spørringene og aggregeringen (ca. linje 142–172) med:

```python
    active_rows = c.execute(f"""
        SELECT omrade, totalpris, {bra_expr} AS bra_num, er_nybygg
        FROM annonser
        WHERE status = 'Aktiv'
          AND totalpris IS NOT NULL
          AND bra IS NOT NULL
          AND {bra_expr} > 0
    """).fetchall()

    sold_rows = c.execute(f"""
        SELECT omrade, totalpris, {bra_expr} AS bra_num, COALESCE(er_nybygg, 0) AS er_nybygg
        FROM solgte
        WHERE solgt_dato >= date('now', '-12 months')
          AND totalpris IS NOT NULL
          AND bra IS NOT NULL
          AND {bra_expr} > 0
    """).fetchall()

    # Aggregate into dicts keyed by omrade
    stats = {}
    for row in active_rows:
        if not row["omrade"]:
            continue
        kvm = round(row["totalpris"] / row["bra_num"])
        entry = stats.setdefault(row["omrade"], {"aktive": [], "solgte": [], "ny_aktive": [], "ny_solgte": []})
        if row["er_nybygg"]:
            entry["ny_aktive"].append(kvm)
        else:
            entry["aktive"].append(kvm)

    for row in sold_rows:
        if not row["omrade"]:
            continue
        kvm = round(row["totalpris"] / row["bra_num"])
        entry = stats.setdefault(row["omrade"], {"aktive": [], "solgte": [], "ny_aktive": [], "ny_solgte": []})
        if row["er_nybygg"]:
            entry["ny_solgte"].append(kvm)
        else:
            entry["solgte"].append(kvm)
```

- [ ] **Step 2: Oppdater build_bins til å inkludere ny_aktive og ny_solgte**

Erstatt `build_bins`-funksjonen (ca. linje 175–189) med:

```python
    def build_bins(aktive, solgte, ny_aktive, ny_solgte):
        all_vals = aktive + solgte + ny_aktive + ny_solgte
        if not all_vals:
            return []
        bin_min = (min(all_vals) // BIN_SIZE) * BIN_SIZE
        bin_max = (max(all_vals) // BIN_SIZE) * BIN_SIZE + BIN_SIZE
        bins = []
        v = bin_min
        while v < bin_max:
            a  = sum(1 for x in aktive    if v <= x < v + BIN_SIZE)
            s  = sum(1 for x in solgte    if v <= x < v + BIN_SIZE)
            na = sum(1 for x in ny_aktive if v <= x < v + BIN_SIZE)
            ns = sum(1 for x in ny_solgte if v <= x < v + BIN_SIZE)
            if a or s or na or ns:
                bins.append({"label": f"{v // 1000}k", "aktive": a, "solgte": s, "ny_aktive": na, "ny_solgte": ns})
            v += BIN_SIZE
        return bins
```

- [ ] **Step 3: Oppdater INSERT-løkken til å bruke alle 4 lister**

Erstatt INSERT-løkken (ca. linje 191–210) med:

```python
    c.execute("DELETE FROM omrade_stats")
    for omrade, data in stats.items():
        all_kvm = data["aktive"] + data["solgte"] + data["ny_aktive"] + data["ny_solgte"]
        if not all_kvm:
            continue
        bins = build_bins(data["aktive"], data["solgte"], data["ny_aktive"], data["ny_solgte"])
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
            json.dumps(bins),
            today,
        ))
    conn.commit()
```

- [ ] **Step 4: Commit**

```bash
git add finn_tracker_db.py
git commit -m "feat: histogram bins now include ny_aktive and ny_solgte per area"
```

---

## Task 4: Oppdater db.py — filter og histogram

**Files:**
- Modify: `db.py:54-109` (get_listings)
- Modify: `db.py:117-127` (get_omrade_histogram_cached)

- [ ] **Step 1: Skriv failing test for er_nybygg-filter**

I `tests/test_db.py`, legg til:

```python
def test_get_listings_filter_brukt_only(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"er_nybygg": ["0"]})
    assert all(r["er_nybygg"] == 0 for r in rows)


def test_get_listings_filter_nybygg_only(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"er_nybygg": ["1"]})
    assert all(r["er_nybygg"] == 1 for r in rows)


def test_get_listings_filter_both_types(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"er_nybygg": ["0", "1"]})
    assert len(rows) == 4  # 3 brukt + 1 nybygg in seed
```

- [ ] **Step 2: Oppdater conftest.py med er_nybygg i schema og seed**

I `tests/conftest.py`, legg til `er_nybygg INTEGER DEFAULT 0` etter `postnummer TEXT` i `CREATE TABLE annonser`-blokken:

```sql
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
            omrade TEXT, postnummer TEXT, er_nybygg INTEGER DEFAULT 0
        );
```

Oppdater eksisterende INSERT-rader til å inkludere `er_nybygg = 0` som siste verdi (de tre seed-radene), og legg til en fjerde rad som er nybygg:

```sql
        INSERT INTO annonser VALUES
            ('111','Møllenberggata 12',2990000,NULL,2990000,55370,3200,NULL,
             'Leilighet','54','2','2. etasje','2026-04-10','2026-04-21',
             11,0,3200000,-210000,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=111',
             'Ole Hansen','DNB Eiendom',NULL,'Prisnedsatt','Møllenberg','7043',0),
            ('222','Elgesetergate 24',3450000,NULL,3450000,56557,NULL,NULL,
             'Leilighet','61','3','1. etasje','2026-04-01','2026-04-21',
             20,2,3450000,0,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=222',
             NULL,NULL,NULL,'14+ dager | 2+ visninger','Elgeseter','7030',0),
            ('333','Nardovegen 8',2650000,1200000,3850000,69737,4500,NULL,
             'Leilighet','38','1','3. etasje','2026-04-18','2026-04-21',
             3,0,2650000,0,'Aktiv',
             'https://finn.no/realestate/homes/ad.html?finnkode=333',
             NULL,NULL,NULL,'Høy fellesgjeld','Nardo','7023',0),
            ('444','Nybyggvegen 1',4500000,NULL,4500000,75000,NULL,NULL,
             'Leilighet','60','3','1. etasje','2026-04-21','2026-04-21',
             0,0,4500000,0,'Aktiv',
             'https://finn.no/realestate/newbuildings/ad.html?finnkode=444',
             NULL,NULL,NULL,NULL,'Møllenberg','7043',1);
```

Oppdater også `test_get_stats_counts` i `test_db.py` — total er nå 4:

```python
def test_get_stats_counts(seeded_app):
    with seeded_app.app_context():
        stats = get_stats()
    assert stats["total"] == 4
    assert stats["flaggede"] == 3
    assert stats["prisnedsatte"] == 1
```

Og `test_get_listings_no_filters_returns_all_active` — default-filter gir nå kun brukt (3):

```python
def test_get_listings_no_filters_returns_all_active(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({})
    assert len(rows) == 3  # default: kun brukt (er_nybygg=0)
```

- [ ] **Step 3: Kjør tester — forvent FAIL**

```bash
pytest tests/test_db.py -v
```

Forventet: `test_get_listings_filter_brukt_only`, `test_get_listings_filter_nybygg_only`, `test_get_listings_filter_both_types` FAILer.

- [ ] **Step 4: Implementer er_nybygg-filter i get_listings()**

I `db.py`, legg til ny blokk etter `status_filter`-blokken og FØR `omrade`-filteret:

```python
    er_nybygg_filter = filters.get("er_nybygg")
    if er_nybygg_filter:
        placeholders = ",".join("?" * len(er_nybygg_filter))
        query += f" AND er_nybygg IN ({placeholders})"
        params.extend(int(v) for v in er_nybygg_filter)
    else:
        query += " AND er_nybygg = 0"
```

- [ ] **Step 5: Kjør tester — forvent PASS**

```bash
pytest tests/test_db.py -v
```

Forventet: alle tester PASSer.

- [ ] **Step 6: Oppdater get_omrade_histogram_cached til å beregne max_count på tvers av alle 4 felt**

I `db.py`, erstatt `max_count`-linjen i `get_omrade_histogram_cached`:

```python
    max_count = max(
        (b.get("aktive", 0) + b.get("solgte", 0) + b.get("ny_aktive", 0) + b.get("ny_solgte", 0))
        for b in bins
    ) if bins else 1
```

- [ ] **Step 7: Commit**

```bash
git add db.py tests/conftest.py tests/test_db.py
git commit -m "feat: filter listings by er_nybygg, update histogram max_count for 4 segments"
```

---

## Task 5: Oppdater app.py til å sende er_nybygg-filter

**Files:**
- Modify: `app.py:43-58` (annonser-ruten)

- [ ] **Step 1: Legg til er_nybygg i filters-dict**

I `app.py`, i `annonser()`-funksjonen, legg til `er_nybygg` i `filters`-dict:

```python
        filters = {
            "omrade":    request.form.get("omrade") or None,
            "pris_min":  request.form.get("pris_min") or None,
            "pris_maks": request.form.get("pris_maks") or None,
            "bra_min":   request.form.get("bra_min") or None,
            "bra_maks":  request.form.get("bra_maks") or None,
            "rom":       request.form.get("rom") or None,
            "flagg":     request.form.getlist("flagg"),
            "status":    request.form.getlist("status") or None,
            "er_nybygg": request.form.getlist("er_nybygg") or None,
        }
```

- [ ] **Step 2: Kjør eksisterende tester**

```bash
pytest tests/ -v
```

Forventet: alle tester PASSer.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: pass er_nybygg filter from POST form to get_listings"
```

---

## Task 6: Legg til toggle-knapper i index.html

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Legg til Boligtype filter-gruppe**

I `templates/index.html`, legg til ny `filter-group` rett FØR `<!-- Sidebar with filters -->` sin lukkende `</form>`-tag (etter Status-gruppen):

```html
      <div class="filter-group">
        <div class="filter-label">Boligtype</div>
        <div class="btn-group">
          <button type="button" class="active" id="btn-brukt"
                  onclick="toggleBoligtype(this, '0')">Brukt</button>
          <button type="button" id="btn-nybygg"
                  onclick="toggleBoligtype(this, '1')">Nybygg</button>
        </div>
        <input type="hidden" name="er_nybygg" value="0" id="er-nybygg-0">
      </div>
```

- [ ] **Step 2: Legg til toggleBoligtype JS-funksjon**

I `<script>`-blokken nederst i `index.html`, legg til:

```javascript
function toggleBoligtype(btn, val) {
  btn.classList.toggle('active');
  const existingInput = document.getElementById('er-nybygg-' + val);
  if (btn.classList.contains('active')) {
    if (!existingInput) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'er_nybygg';
      input.value = val;
      input.id = 'er-nybygg-' + val;
      document.getElementById('filter-form').appendChild(input);
    }
  } else {
    if (existingInput) existingInput.remove();
  }
  htmx.trigger('#filter-form', 'change');
}
```

- [ ] **Step 3: Oppdater resetFilters() til å nullstille boligtype**

I den eksisterende `resetFilters()`-funksjonen, legg til på slutten:

```javascript
  // Reset boligtype — Brukt aktiv, Nybygg inaktiv
  document.getElementById('btn-brukt').classList.add('active');
  document.getElementById('btn-nybygg').classList.remove('active');
  const nyInput = document.getElementById('er-nybygg-1');
  if (nyInput) nyInput.remove();
  if (!document.getElementById('er-nybygg-0')) {
    const input = document.createElement('input');
    input.type = 'hidden'; input.name = 'er_nybygg'; input.value = '0';
    input.id = 'er-nybygg-0';
    document.getElementById('filter-form').appendChild(input);
  }
```

- [ ] **Step 4: Test manuelt i nettleser**

Start Flask (`python app.py`) og åpne http://127.0.0.1:5000.
- Verifiser at "Brukt"-knappen er uthevet ved oppstart.
- Klikk "Nybygg" — begge skal være aktive, og listen skal oppdatere seg.
- Klikk "Brukt" for å skjule brukt — kun nybygg skal vises.
- Klikk "Nullstill filtre" — Brukt skal bli aktiv igjen, Nybygg inaktiv.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html
git commit -m "feat: add Brukt/Nybygg toggle filter to sidebar"
```

---

## Task 7: Oppdater style.css med nybygg-farger

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Legg til farger for nybygg-segmenter**

I `static/style.css`, legg til etter `.hist-solgt-dot { background: #f97316; }`:

```css
.hist-ny-aktiv { background: #4ade80; }
.hist-ny-solgt { background: #16a34a; }
.hist-ny-aktiv-dot { background: #4ade80; }
.hist-ny-solgt-dot { background: #16a34a; }
.hist-legend-item { display: inline-flex; align-items: center; gap: 4px; cursor: pointer; user-select: none; transition: opacity 0.15s; }
.hist-legend-item.disabled { opacity: 0.35; }
```

- [ ] **Step 2: Commit**

```bash
git add static/style.css
git commit -m "feat: add light/dark green CSS classes for nybygg histogram segments"
```

---

## Task 8: Oppdater omrade_histogram.html med 4 segmenter og klikkbar legende

**Files:**
- Modify: `templates/omrade_histogram.html`

- [ ] **Step 1: Erstatt hele omrade_histogram.html**

```html
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
  </div>
</div>

<script>
function toggleHistSeg(legendItem) {
  const seg = legendItem.dataset.seg;
  const isDisabled = legendItem.classList.toggle('disabled');
  document.querySelectorAll('[data-seg="' + seg + '"]').forEach(el => {
    if (el !== legendItem) {
      el.style.display = isDisabled ? 'none' : '';
    }
  });
}
</script>
```

- [ ] **Step 2: Test manuelt i nettleser**

Åpne http://127.0.0.1:5000/områder og klikk på et område for å åpne histogrammet.
- Verifiser at alle 4 fargesegmenter vises (blå, oransje, lysegrønn, mørkegrønn).
- Klikk på hvert legend-element — tilhørende segmenter skal skjules/vises.
- Legenden skal bli transparent (opacity 0.35) når segmentet er deaktivert.

- [ ] **Step 3: Commit**

```bash
git add templates/omrade_histogram.html
git commit -m "feat: histogram shows 4 segments (brukt/nybygg × aktiv/solgt) with clickable legend"
```

---

## Task 9: Kjør alle tester og verifiser

- [ ] **Step 1: Kjør hele test-suiten**

```bash
pytest tests/ -v
```

Forventet: alle tester PASSer.

- [ ] **Step 2: Start Flask og gjør en rask end-to-end sjekk**

```bash
python app.py
```

Sjekkliste:
- [ ] Forsidesiden laster med Brukt aktivt som standard
- [ ] Toggle Nybygg — listen oppdateres via HTMX
- [ ] Nullstill filtre — Brukt aktiv, Nybygg inaktiv
- [ ] `/områder` — histogrammet har 4 segmenter
- [ ] Klikk legend — segmenter toggler av/på

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat: full nybygg support — scraper, filter, histogram"
```
