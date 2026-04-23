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
    assert stats["total"] == 4   # was 3, now 4 (3 brukt + 1 nybygg)
    assert stats["flaggede"] == 3
    assert stats["prisnedsatte"] == 1


def test_get_listings_no_filters_returns_all_active(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({})
    assert len(rows) == 3  # default: only brukt (er_nybygg=0)


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


import sqlite3
import json as _json
from datetime import date as _date
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
    today = str(_date.today())
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
    data = _json.loads(row["histogram_json"])

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


def test_get_omrade_histogram_cached_returns_new_fields(seeded_app):
    # PSEUDOCODE:
    # 1. Insert a new-format histogram_json row into omrade_stats
    # 2. Call get_omrade_histogram_cached for that omrade
    # 3. Assert the returned dict includes bin_start, brukt_avg, brukt_median, etc.
    from db import get_omrade_histogram_cached, get_db
    histogram_data = {
        "bins": [{"label": "40k", "aktive": 2, "solgte": 1, "ny_aktive": 0, "ny_solgte": 0}],
        "bin_start": 40000,
        "brukt_avg": 42000, "brukt_median": 41000,
        "ny_avg": None, "ny_median": None,
        "alle_avg": 42000, "alle_median": 41000,
    }
    with seeded_app.app_context():
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
