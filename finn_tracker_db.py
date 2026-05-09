"""
Finn-tracker med SQLite-lagring — grunnlag for fremtidig nettside.
Scraping-logikk importeres fra scraper.py.
"""

import sqlite3
import re
import os
import json
import statistics
from datetime import date, datetime
from playwright.sync_api import sync_playwright
from scraper import fetch_all_listings, scrape_ad, check_sold_status

DB_FILE = "finn_tracker.db"


# ─── Database-oppsett ─────────────────────────────────────────────────────────

# PSEUDOCODE:
# 1. Open a connection to the SQLite database file
# 2. Set row_factory to sqlite3.Row so rows can be accessed by column name
# 3. Return the connection
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# PSEUDOCODE:
# 1. Open a database connection
# 2. Create tables if they don't exist: annonser, prishistorikk, solgte, omrade_stats
# 3. Run migrations to add columns that may be missing from older schemas
# 4. Commit and close the connection
def init_db():
    conn = get_conn()
    c = conn.cursor()

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
            er_nybygg       INTEGER DEFAULT 0,
            lat             REAL,
            lon             REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prishistorikk (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            finnkode      TEXT,
            dato          DATE,
            prisantydning INTEGER,
            totalpris     INTEGER
        )
    """)

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
            er_nybygg       INTEGER DEFAULT 0,
            solgt_dato      DATE,
            arsak           TEXT,
            lat             REAL,
            lon             REAL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS hendelser (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            finnkode  TEXT NOT NULL,
            dato      DATE NOT NULL,
            type      TEXT NOT NULL,
            detaljer  TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS run_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at      TIMESTAMP NOT NULL,
            finished_at     TIMESTAMP,
            status          TEXT NOT NULL DEFAULT 'running',
            total_in_search INTEGER DEFAULT 0,
            new_count       INTEGER DEFAULT 0,
            updated_count   INTEGER DEFAULT 0,
            sold_count      INTEGER DEFAULT 0,
            error_message   TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS omrade_stats (
            omrade          TEXT PRIMARY KEY,
            antall_aktive   INTEGER DEFAULT 0,
            antall_solgte   INTEGER DEFAULT 0,
            snitt_kvm_pris  INTEGER,
            min_kvm_pris    INTEGER,
            max_kvm_pris    INTEGER,
            histogram_json  TEXT,
            oppdatert       DATE
        )
    """)
    # Migration: add histogram_json if upgrading from older schema
    try:
        c.execute("ALTER TABLE omrade_stats ADD COLUMN histogram_json TEXT")
    except Exception:
        pass  # Column already exists

    # Migration: add er_nybygg if upgrading from older schema
    try:
        c.execute("ALTER TABLE annonser ADD COLUMN er_nybygg INTEGER DEFAULT 0")
    except Exception:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE solgte ADD COLUMN er_nybygg INTEGER DEFAULT 0")
    except Exception:
        pass  # Column already exists

    # Migration: add lat/lon for the interactive map
    for table in ("annonser", "solgte"):
        for col in ("lat", "lon"):
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} REAL")
            except Exception:
                pass  # Column already exists

    # Migration: convert prishistorikk → hendelser (one-time)
    migrate_prishistorikk_to_hendelser(conn)

    conn.commit()
    conn.close()


# PSEUDOCODE:
# 1. Check if migration is needed (hendelser is empty and prishistorikk has data)
# 2. For each finnkode in prishistorikk, scan rows ordered by dato
# 3. First row → publisert event
# 4. Any row where prisantydning differs from previous → prisendring event
# 5. Duplicate rows (same price) → discarded
# 6. For each listing in solgte, create a solgt/trukket/ukjent event
def migrate_prishistorikk_to_hendelser(conn):
    c = conn.cursor()

    has_hendelser = c.execute("SELECT COUNT(*) FROM hendelser").fetchone()[0]
    has_historikk = c.execute("SELECT COUNT(*) FROM prishistorikk").fetchone()[0]
    if has_hendelser > 0 or has_historikk == 0:
        return  # Already migrated or nothing to migrate

    finnkoder = c.execute(
        "SELECT DISTINCT finnkode FROM prishistorikk ORDER BY finnkode"
    ).fetchall()

    for (finnkode,) in finnkoder:
        rows = c.execute(
            "SELECT dato, prisantydning FROM prishistorikk WHERE finnkode = ? ORDER BY dato",
            (finnkode,)
        ).fetchall()

        prev_pris = None
        for i, row in enumerate(rows):
            if i == 0:
                # First row → publisert
                c.execute(
                    "INSERT INTO hendelser (finnkode, dato, type, detaljer) VALUES (?, ?, ?, ?)",
                    (finnkode, row["dato"], "publisert", None)
                )
            if row["prisantydning"] and prev_pris and row["prisantydning"] != prev_pris:
                detaljer = json.dumps({"fra": prev_pris, "til": row["prisantydning"]})
                c.execute(
                    "INSERT INTO hendelser (finnkode, dato, type, detaljer) VALUES (?, ?, ?, ?)",
                    (finnkode, row["dato"], "prisendring", detaljer)
                )
            prev_pris = row["prisantydning"]

    # Migrate solgte entries
    solgte_rows = c.execute(
        "SELECT finnkode, solgt_dato, arsak FROM solgte WHERE solgt_dato IS NOT NULL"
    ).fetchall()
    for row in solgte_rows:
        c.execute(
            "INSERT INTO hendelser (finnkode, dato, type, detaljer) VALUES (?, ?, ?, ?)",
            (row["finnkode"], row["solgt_dato"], row["arsak"].lower(), None)
        )

    count = c.execute("SELECT COUNT(*) FROM hendelser").fetchone()[0]
    print(f"  Migration: created {count} events from prishistorikk + solgte")


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
LAV_KVM_LABEL = "Lav kr/m²"


# PSEUDOCODE:
# 1. Read each area's alle_q1 (lower quartile) from omrade_stats
# 2. For each active listing, recompute its flag string:
#    - Drop any existing "Lav kr/m²" first
#    - If kvm_pris is known and below the area's Q1, add "Lav kr/m²" back
# 3. Write back any rows whose flagg actually changed
# Must be called AFTER update_omrade_stats since it depends on the freshly
# computed Q1 values.
def update_lav_kvm_flag(conn):
    c = conn.cursor()
    q1_per_area = {}
    for omrade, hjson in c.execute(
        "SELECT omrade, histogram_json FROM omrade_stats"
    ).fetchall():
        try:
            data = json.loads(hjson or "{}")
        except Exception:
            continue
        q1 = data.get("alle_q1")
        if q1 is not None:
            q1_per_area[omrade] = q1

    rows = c.execute(
        "SELECT finnkode, omrade, kvm_pris, flagg FROM annonser WHERE status = 'Aktiv'"
    ).fetchall()
    updates = []
    for finnkode, omrade, kvm_pris, flagg in rows:
        existing = [f.strip() for f in (flagg or "").split("|") if f.strip()]
        existing = [f for f in existing if f != LAV_KVM_LABEL]
        q1 = q1_per_area.get(omrade)
        if kvm_pris is not None and q1 is not None and kvm_pris < q1:
            existing.append(LAV_KVM_LABEL)
        new_flagg = " | ".join(existing) if existing else None
        if new_flagg != flagg:
            updates.append((new_flagg, finnkode))
    if updates:
        c.executemany("UPDATE annonser SET flagg = ? WHERE finnkode = ?", updates)
        conn.commit()
    print(f"  '{LAV_KVM_LABEL}' flag oppdatert for {len(updates)} annonser")


def update_omrade_stats(conn):
    BIN_SIZE = 2000
    today = str(date.today())
    c = conn.cursor()

    print("\n  Oppdaterer områdestatistikk...")

    # bra values are stored as e.g. "41 m² (BRA-i)"; SUBSTR+INSTR extracts the leading integer
    bra_expr = "CAST(TRIM(SUBSTR(bra, 1, INSTR(bra || ' ', ' ') - 1)) AS INTEGER)"

    print("  [1/4] Henter aktive annonser fra databasen...")
    active_rows = c.execute(f"""
        SELECT omrade, totalpris, {bra_expr} AS bra_num, er_nybygg
        FROM annonser
        WHERE status = 'Aktiv'
          AND totalpris IS NOT NULL
          AND bra IS NOT NULL
          AND {bra_expr} > 0
    """).fetchall()

    print("  [2/4] Henter solgte annonser (siste 12 mnd)...")
    sold_rows = c.execute(f"""
        SELECT omrade, totalpris, {bra_expr} AS bra_num, COALESCE(er_nybygg, 0) AS er_nybygg
        FROM solgte
        WHERE solgt_dato >= date('now', '-12 months')
          AND totalpris IS NOT NULL
          AND bra IS NOT NULL
          AND {bra_expr} > 0
    """).fetchall()
    print(f"       {len(active_rows)} aktive, {len(sold_rows)} solgte funnet")

    print("  [3/4] Aggregerer per område...")
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

    # Drop outliers up-front. Two layers of protection:
    #   1. Hard cap at 200k kr/m² — anything above is a clear data error.
    #   2. Per-area 99th-percentile cap — trims the long thin tail so the
    #      histogram's x-axis stays tight around real data and bins are
    #      readable. Only kicks in when there are enough rows to estimate.
    KVM_MAX = 200_000
    for entry in stats.values():
        for key in ("aktive", "solgte", "ny_aktive", "ny_solgte"):
            entry[key] = [x for x in entry[key] if x <= KVM_MAX]
        all_vals = entry["aktive"] + entry["solgte"] + entry["ny_aktive"] + entry["ny_solgte"]
        if len(all_vals) >= 20:
            # 98th percentile drops the long thin tail (sparse outlier clusters
            # like a handful of listings at the top of the price range that
            # would otherwise stretch the x-axis and squash the main bars).
            cap = sorted(all_vals)[int(len(all_vals) * 0.98)]
            for key in ("aktive", "solgte", "ny_aktive", "ny_solgte"):
                entry[key] = [x for x in entry[key] if x <= cap]

    # Compute a global x-axis range so all area histograms share the same
    # start/end on screen. Makes it easy to compare distributions across areas.
    global_vals = []
    for entry in stats.values():
        global_vals.extend(entry["aktive"] + entry["solgte"] + entry["ny_aktive"] + entry["ny_solgte"])
    if global_vals:
        global_min = (min(global_vals) // BIN_SIZE) * BIN_SIZE
        global_max = (max(global_vals) // BIN_SIZE) * BIN_SIZE
    else:
        global_min = global_max = 0

    # Build histogram bins. Uses the GLOBAL min/max so every area renders on
    # the same x-axis; areas with narrower data simply have empty trailing or
    # leading bins. bin_start is needed for the avg/median line positioning.
    def build_bins(aktive, solgte, ny_aktive, ny_solgte):
        all_vals = aktive + solgte + ny_aktive + ny_solgte
        if not all_vals:
            return [], None

        counts = {}
        for lst_idx, lst in enumerate([aktive, solgte, ny_aktive, ny_solgte]):
            for x in lst:
                bin_idx = (x - global_min) // BIN_SIZE
                if bin_idx not in counts:
                    counts[bin_idx] = [0, 0, 0, 0]
                counts[bin_idx][lst_idx] += 1

        # Emit DENSE bins covering [global_min, global_max] — empty bins are zero.
        # Linear price axis is required for the avg/median dotted lines to land in
        # the right place; shared range across areas makes them comparable.
        bin_count = (global_max - global_min) // BIN_SIZE + 1
        bins = []
        for bin_idx in range(bin_count):
            v = global_min + bin_idx * BIN_SIZE
            c = counts.get(bin_idx, [0, 0, 0, 0])
            bins.append({"label": f"{v // 1000}k", "aktive": c[0], "solgte": c[1], "ny_aktive": c[2], "ny_solgte": c[3]})
        return bins, global_min

    def calc_avg(vals):
        return round(sum(vals) / len(vals)) if vals else None

    def calc_median(vals):
        return round(statistics.median(vals)) if vals else None

    def calc_q1(vals):
        # Need at least 2 values for statistics.quantiles
        if not vals or len(vals) < 2:
            return None
        return round(statistics.quantiles(vals, n=4)[0])

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
            "brukt_q1":     calc_q1(brukt),
            "ny_avg":       calc_avg(nybygg),
            "ny_median":    calc_median(nybygg),
            "ny_q1":        calc_q1(nybygg),
            "alle_avg":     calc_avg(all_kvm),
            "alle_median":  calc_median(all_kvm),
            "alle_q1":      calc_q1(all_kvm),
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


# ─── Lese/skrive data ─────────────────────────────────────────────────────────

# PSEUDOCODE:
# 1. Query all rows from the annonser table
# 2. Return a dict mapping finnkode -> row data for quick lookup
def load_existing(conn):
    """Returner dict med eksisterende annonser: {finnkode: row}."""
    c = conn.cursor()
    c.execute("SELECT * FROM annonser")
    return {row["finnkode"]: dict(row) for row in c.fetchall()}


# PSEUDOCODE:
# 1. Set defaults for first_seen, starting price, and viewing count
# 2. If the listing already exists, inherit first_seen and starting price from old data
# 3. If the next viewing date changed, increment the viewing counter
# 4. Calculate days on market from first_seen to today
# 5. Calculate price change from starting price to current asking price
# 6. Calculate kvm_pris (kr/m²) from totalpris and living area (bra)
# 7. Build a list of flags (price reduced, 14+ days, 2+ viewings, high shared debt)
# 8. Log events to hendelser: publisert (new/re-appeared), prisendring, visning
# 9. Upsert the listing into the annonser table (insert or update on conflict)
def upsert_listing(conn, finnkode, ad, today, existing=None):
    """Sett inn ny eller oppdater eksisterende annonse."""
    forste_sett = today
    pris_ved_start = ad.get("prisantydning")
    antall_visninger = 0

    if existing:
        forste_sett = existing.get("forste_sett") or today
        if isinstance(forste_sett, str):
            forste_sett = date.fromisoformat(forste_sett)
        pris_ved_start = existing.get("pris_ved_start") or ad.get("prisantydning")
        antall_visninger = existing.get("antall_visninger") or 0
        forrige_visning = existing.get("neste_visning")
        ny_visning = ad.get("neste_visning")
        if ny_visning and ny_visning != forrige_visning:
            antall_visninger += 1

    # --- Event detection ---
    if not existing:
        # New listing — log publisert
        log_event(conn, finnkode, today, "publisert")
    else:
        # Re-appeared after being sold/withdrawn
        if existing.get("status") in ("Solgt", "Trukket", "Ukjent"):
            log_event(conn, finnkode, today, "publisert")

        # Price changed — compare current prisantydning to existing
        old_pris = existing.get("prisantydning")
        new_pris = ad.get("prisantydning")
        if old_pris and new_pris and old_pris != new_pris:
            log_event(conn, finnkode, today, "prisendring", {"fra": old_pris, "til": new_pris})

        # New viewing detected
        forrige = existing.get("neste_visning")
        ny = ad.get("neste_visning")
        if ny and ny != forrige:
            log_event(conn, finnkode, today, "visning", {"visningsdato": ny})

    if isinstance(forste_sett, datetime):
        forste_sett = forste_sett.date()
    dager = (today - forste_sett).days if isinstance(forste_sett, date) else 0

    prisendring = None
    if pris_ved_start and ad.get("prisantydning"):
        prisendring = ad["prisantydning"] - pris_ved_start

    kvm_pris = None
    bra_str = ad.get("bra")
    if bra_str and ad.get("totalpris"):
        bra_match = re.search(r"(\d+)", str(bra_str))
        if bra_match:
            bra_num = int(bra_match.group(1))
            if bra_num > 0:
                kvm_pris = round(ad["totalpris"] / bra_num)

    flagg = []
    if prisendring and prisendring < 0:
        flagg.append("Prisnedsatt")
    if dager >= 14:
        flagg.append("14+ dager")
    if antall_visninger >= 2:
        flagg.append("2+ visninger")
    if ad.get("totalpris") and ad.get("fellesgjeld") and ad["fellesgjeld"] / ad["totalpris"] >= 0.30:
        flagg.append("Høy fellesgjeld")

    c = conn.cursor()
    c.execute("""
        INSERT INTO annonser (
            finnkode, adresse, prisantydning, fellesgjeld, totalpris, kvm_pris,
            felleskost, fellesformue, type, bra, rom, etasje,
            forste_sett, siste_sett, dager_ute, antall_visninger,
            pris_ved_start, prisendring, status, url,
            megler, meglerkontor, neste_visning, flagg, omrade, postnummer, er_nybygg,
            lat, lon
        ) VALUES (
            :finnkode, :adresse, :prisantydning, :fellesgjeld, :totalpris, :kvm_pris,
            :felleskost, :fellesformue, :type, :bra, :rom, :etasje,
            :forste_sett, :siste_sett, :dager_ute, :antall_visninger,
            :pris_ved_start, :prisendring, :status, :url,
            :megler, :meglerkontor, :neste_visning, :flagg, :omrade, :postnummer, :er_nybygg,
            :lat, :lon
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
            er_nybygg       = excluded.er_nybygg,
            lat             = COALESCE(excluded.lat, annonser.lat),
            lon             = COALESCE(excluded.lon, annonser.lon)
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
        "lat":              ad.get("lat"),
        "lon":              ad.get("lon"),
    })


# PSEUDOCODE:
# 1. Insert a row into the hendelser table with finnkode, date, event type, and optional JSON details
# 2. If detaljer is a dict, serialize it to a JSON string before inserting
def log_event(conn, finnkode, dato, event_type, detaljer=None):
    c = conn.cursor()
    detaljer_json = json.dumps(detaljer) if isinstance(detaljer, dict) else detaljer
    c.execute(
        "INSERT INTO hendelser (finnkode, dato, type, detaljer) VALUES (?, ?, ?, ?)",
        (finnkode, str(dato), event_type, detaljer_json)
    )



# PSEUDOCODE:
# 1. Look up the listing in annonser by finnkode
# 2. If not found, return early
# 3. Copy the full listing row into the solgte table with sold date and reason
# 4. Update the listing's status in annonser to the sold reason (Solgt/Trukket/Ukjent)
# 5. Log a solgt/trukket/ukjent event to hendelser
def mark_sold(conn, finnkode, today, arsak):
    c = conn.cursor()
    c.execute("SELECT * FROM annonser WHERE finnkode = ?", (finnkode,))
    row = c.fetchone()
    if not row:
        return
    row = dict(row)
    c.execute("""
        INSERT INTO solgte (
            finnkode, adresse, prisantydning, fellesgjeld, totalpris, kvm_pris,
            felleskost, fellesformue, type, bra, rom, etasje,
            forste_sett, siste_sett, dager_ute, antall_visninger,
            pris_ved_start, prisendring, status, url,
            megler, meglerkontor, neste_visning, flagg, omrade, postnummer,
            er_nybygg, solgt_dato, arsak, lat, lon
        ) VALUES (
            :finnkode, :adresse, :prisantydning, :fellesgjeld, :totalpris, :kvm_pris,
            :felleskost, :fellesformue, :type, :bra, :rom, :etasje,
            :forste_sett, :siste_sett, :dager_ute, :antall_visninger,
            :pris_ved_start, :prisendring, :status, :url,
            :megler, :meglerkontor, :neste_visning, :flagg, :omrade, :postnummer,
            :er_nybygg, :solgt_dato, :arsak, :lat, :lon
        )
    """, {**row, "solgt_dato": str(today), "arsak": arsak})

    c.execute(
        "UPDATE annonser SET status = ? WHERE finnkode = ?",
        (arsak, finnkode)
    )

    log_event(conn, finnkode, today, arsak.lower())


# ─── Main ─────────────────────────────────────────────────────────────────────

# PSEUDOCODE:
# 1. Initialize the database (create tables if needed)
# 2. Launch a headless Playwright browser and fetch all listing URLs from Finn.no search
# 3. Load existing listings from the database for comparison
# 4. For each listing in search results, scrape the detail page and upsert into the database
# 5. For each existing active listing NOT in today's search results, check if it was sold
# 6. Update the omrade_stats aggregation table
# 7. Print a summary of new, updated, and sold listings
def main():
    today = date.today()
    print(f"\n=== Finn-tracker (DB) kjøres {today} ===\n")

    init_db()
    conn = get_conn()

    # Log the start of this run
    run_started = datetime.now()
    conn.execute(
        "INSERT INTO run_log (started_at, status) VALUES (?, 'running')",
        (run_started.isoformat(),),
    )
    conn.commit()
    run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        pg = context.new_page()

        print("Henter søkeresultater fra Finn.no...")
        try:
            listings = fetch_all_listings(pg)
        except Exception as e:
            print(f"FEIL ved henting av søkeside: {e}")
            conn.execute(
                "UPDATE run_log SET finished_at=?, status='failed', error_message=? WHERE id=?",
                (datetime.now().isoformat(), str(e), run_id),
            )
            conn.commit()
            browser.close()
            conn.close()
            return

        print(f"  Fant {len(listings)} annonser i søket.\n")

        existing = load_existing(conn)
        found_codes = {l["finnkode"] for l in listings}
        new_count = 0
        updated_count = 0
        sold_count = 0

        try:
            for i, listing in enumerate(listings, 1):
                finnkode = listing["finnkode"]
                url = listing["url"]
                print(f"  [{i}/{len(listings)}] Henter {finnkode}...", end=" ", flush=True)
                ad = scrape_ad(pg, url)
                if not ad:
                    print("ingen data, hopper over.")
                    continue

                is_new = finnkode not in existing
                status = "ny" if is_new else "oppdaterer"
                print(f"{status}  |  {ad.get('adresse', '')}  |  postnr={ad.get('postnummer')}  område={ad.get('omrade')}")

                ad["er_nybygg"] = listing.get("er_nybygg", 0)
                upsert_listing(conn, finnkode, ad, today, existing.get(finnkode))
                conn.commit()

                if is_new:
                    new_count += 1
                else:
                    updated_count += 1

            # Sjekk om noen eksisterende annonser er borte fra søket
            for finnkode, info in existing.items():
                if finnkode not in found_codes and info.get("status") in ("Aktiv", "Ukjent"):
                    ad_url = f"https://www.finn.no/realestate/homes/ad.html?finnkode={finnkode}"
                    arsak = check_sold_status(pg, ad_url)
                    mark_sold(conn, finnkode, today, arsak)
                    conn.commit()
                    print(f"  {finnkode} ikke lenger i søk — status: {arsak}")
                    sold_count += 1

        finally:
            try:
                update_omrade_stats(conn)
            except Exception as e:
                print(f"  ADVARSEL: update_omrade_stats feilet: {e}")
            try:
                update_lav_kvm_flag(conn)
            except Exception as e:
                print(f"  ADVARSEL: update_lav_kvm_flag feilet: {e}")

            # Log the completed run
            conn.execute(
                """UPDATE run_log
                   SET finished_at=?, status='success',
                       total_in_search=?, new_count=?,
                       updated_count=?, sold_count=?
                   WHERE id=?""",
                (datetime.now().isoformat(), len(listings),
                 new_count, updated_count, sold_count, run_id),
            )
            conn.commit()

            browser.close()
            conn.close()
            print(f"\n=== Ferdig ===")
            print(f"  Nye annonser:     {new_count}")
            print(f"  Oppdaterte:       {updated_count}")
            print(f"  Solgt/trukket:    {sold_count}")
            print(f"  Lagret til:       {DB_FILE}\n")


if __name__ == "__main__":
    main()
