import sqlite3
import json
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
# 2. Query listings first seen today (forste_sett = today) — i.e. genuinely new,
#    not just scraped today
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
        "SELECT COUNT(*) FROM annonser WHERE forste_sett = ? AND status = 'Aktiv'",
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
# Translate the filter dict into a WHERE-clause fragment + matching params list.
# Both get_listings() and get_listings_with_coords() share this so the filter
# semantics stay identical between list view and map view.
def _build_where(filters):
    where = ""
    params = []

    status_filter = filters.get("status")
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        where += f" AND status IN ({placeholders})"
        params.extend(status_filter)
    else:
        where += " AND status = 'Aktiv'"

    er_nybygg_filter = filters.get("er_nybygg")
    if er_nybygg_filter:
        placeholders = ",".join("?" * len(er_nybygg_filter))
        where += f" AND er_nybygg IN ({placeholders})"
        params.extend(int(v) for v in er_nybygg_filter)
    else:
        where += " AND er_nybygg = 0"

    if filters.get("kun_nye"):
        where += " AND forste_sett = ?"
        params.append(str(date.today()))

    if filters.get("sok"):
        like = f"%{filters['sok'].lower()}%"
        where += (" AND (LOWER(adresse) LIKE ?"
                  " OR LOWER(finnkode) LIKE ?"
                  " OR LOWER(omrade) LIKE ?)")
        params.extend([like, like, like])

    if filters.get("omrade"):
        where += " AND omrade = ?"
        params.append(filters["omrade"])

    if filters.get("prisantydning_min"):
        where += " AND prisantydning >= ?"
        params.append(int(filters["prisantydning_min"]))
    if filters.get("prisantydning_maks"):
        where += " AND prisantydning <= ?"
        params.append(int(filters["prisantydning_maks"]))
    if filters.get("totalpris_min"):
        where += " AND totalpris >= ?"
        params.append(int(filters["totalpris_min"]))
    if filters.get("totalpris_maks"):
        where += " AND totalpris <= ?"
        params.append(int(filters["totalpris_maks"]))
    if filters.get("felleskost_maks"):
        where += " AND felleskost <= ?"
        params.append(int(filters["felleskost_maks"]))
    if filters.get("bra_min"):
        where += " AND CAST(bra AS INTEGER) >= ?"
        params.append(int(filters["bra_min"]))
    if filters.get("bra_maks"):
        where += " AND CAST(bra AS INTEGER) <= ?"
        params.append(int(filters["bra_maks"]))

    rom = filters.get("rom")
    if rom and rom != "alle":
        if rom == "3+":
            where += " AND CAST(rom AS INTEGER) >= 3"
        else:
            where += " AND CAST(rom AS INTEGER) = ?"
            params.append(int(rom))

    for flag in filters.get("flagg", []):
        where += " AND flagg LIKE ?"
        params.append(f"%{flag}%")

    return where, params


# PSEUDOCODE:
# 1. Build WHERE clause via _build_where
# 2. Apply sort order (default: siste_sett DESC)
# 3. Return list of row dicts
def get_listings(filters, sort="siste_sett_desc"):
    where, params = _build_where(filters)
    sort_map = {
        "siste_sett_desc": "siste_sett DESC",
        "prisantydning_asc": "prisantydning ASC",
        "prisantydning_desc": "prisantydning DESC",
        "dager_ute_desc": "dager_ute DESC",
    }
    query = (
        "SELECT * FROM annonser WHERE 1=1" + where
        + f" ORDER BY {sort_map.get(sort, 'siste_sett DESC')}"
    )

    conn = get_db()
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


# PSEUDOCODE:
# Same filter contract as get_listings, but only returns rows with coords + a
# slim column set suitable for sending as JSON to the map page.
def get_listings_with_coords(filters):
    where, params = _build_where(filters)
    query = (
        "SELECT finnkode, adresse, omrade, lat, lon, prisantydning, totalpris,"
        " kvm_pris, bra, rom, flagg"
        " FROM annonser"
        " WHERE 1=1 AND lat IS NOT NULL AND lon IS NOT NULL" + where
    )
    conn = get_db()
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


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
    keys = ("bin_start", "brukt_avg", "brukt_median", "brukt_q1",
            "ny_avg", "ny_median", "ny_q1",
            "alle_avg", "alle_median", "alle_q1")
    if isinstance(raw, list):
        bins = raw
        extra = {k: None for k in keys}
    else:
        bins = raw.get("bins", [])
        extra = {k: raw.get(k) for k in keys}
    # Histogram only renders brukt aktive/solgte (nybygg segments are excluded
     # from the chart), so size bars relative to the max brukt count per bin.
    max_count = max(
        (b.get("aktive", 0) + b.get("solgte", 0)) for b in bins
    ) if bins else 1
    max_count = max(max_count, 1)
    return {"bins": bins, "max_count": max_count, **extra}


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
# 1. Query hendelser for the given finnkode, ordered by date ascending
# 2. Parse the detaljer JSON string into a dict for each row
# 3. Return list of event dicts
def get_events(finnkode):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM hendelser WHERE finnkode = ? ORDER BY dato ASC, id ASC",
        (finnkode,)
    ).fetchall()
    conn.close()
    events = []
    for row in rows:
        event = dict(row)
        if event["detaljer"]:
            event["detaljer"] = json.loads(event["detaljer"])
        events.append(event)
    return events


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


# PSEUDOCODE:
# 1. Read all rows from omrade_stats
# 2. Apply sort: navn_asc (default), snitt_desc, antall_desc
# 3. Return list of dicts
def get_omrade_stats(sort="navn_asc"):
    sort_map = {
        "navn_asc":    "omrade ASC",
        "snitt_desc":  "snitt_kvm_pris DESC",
        "antall_desc": "(antall_aktive + antall_solgte) DESC",
    }
    order = sort_map.get(sort, "omrade ASC")
    conn = get_db()
    rows = conn.execute(
        f"SELECT * FROM omrade_stats ORDER BY {order}"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
