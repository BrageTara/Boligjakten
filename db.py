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

    er_nybygg_filter = filters.get("er_nybygg")
    if er_nybygg_filter:
        placeholders = ",".join("?" * len(er_nybygg_filter))
        query += f" AND er_nybygg IN ({placeholders})"
        params.extend(int(v) for v in er_nybygg_filter)
    else:
        query += " AND er_nybygg = 0"

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
