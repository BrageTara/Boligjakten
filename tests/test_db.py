import pytest
from db import get_stats, get_listings, get_listings_with_coords, get_listing, get_price_history, get_sold_listings


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


def test_get_listings_filter_by_prisantydning(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"prisantydning_maks": 3000000})
    assert len(rows) == 2  # 111 (2.99M) and 333 (2.65M); 222 (3.45M) excluded


def test_get_listings_filter_by_totalpris(seeded_app):
    # Listing 333 has prisantydning=2.65M but totalpris=3.85M (1.2M fellesgjeld),
    # so totalpris_maks must exclude it where prisantydning_maks would not.
    with seeded_app.app_context():
        rows = get_listings({"totalpris_maks": 3000000})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"111"}


def test_get_listings_filter_by_prisantydning_and_totalpris(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({
            "prisantydning_min": 2000000,
            "prisantydning_maks": 3000000,
            "totalpris_maks": 3000000,
        })
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"111"}


def test_get_listings_filter_sok_by_address(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"sok": "elgeseter"})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"222"}  # adresse: Elgesetergate 24


def test_get_listings_filter_sok_by_finnkode(seeded_app):
    with seeded_app.app_context():
        rows = get_listings({"sok": "333"})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"333"}


def test_get_listings_filter_sok_by_omrade(seeded_app):
    # 444 is nybygg, so include both er_nybygg values
    with seeded_app.app_context():
        rows = get_listings({"sok": "møllenberg", "er_nybygg": ["0", "1"]})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"111", "444"}  # both in Møllenberg


def test_get_listings_filter_by_felleskost(seeded_app):
    # Seed: 111 felleskost=3200, 333 felleskost=4500, 222 + 444 are NULL.
    # NULL rows must be excluded — user setting a max can't make claims about unknowns.
    with seeded_app.app_context():
        rows = get_listings({"felleskost_maks": 4000})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"111"}


def test_get_listings_filter_kun_nye(seeded_app, monkeypatch):
    # Pin "today" to a known date and seed listing 444 has forste_sett=2026-04-21
    import db
    from datetime import date
    class FakeDate(date):
        @classmethod
        def today(cls):
            return date(2026, 4, 21)
    monkeypatch.setattr(db, "date", FakeDate)
    with seeded_app.app_context():
        rows = get_listings({"kun_nye": "1", "er_nybygg": ["0", "1"]})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"444"}  # only 444 has forste_sett == 2026-04-21


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

    # statistics.quantiles uses exclusive method by default
    # alle [80000,100000,120000,140000] → Q1 = 85000
    assert data["alle_q1"] == 85000
    # brukt [80000,100000,120000] → Q1 = 80000
    assert data["brukt_q1"] == 80000
    # nybygg has only 1 value → q1 is None (needs >=2)
    assert data["ny_q1"] is None

    conn.close()


def test_get_listings_with_coords_excludes_null_coords(seeded_app):
    # Listing 333 has NULL lat/lon, so should be filtered out.
    with seeded_app.app_context():
        rows = get_listings_with_coords({})
    finnkoder = {r["finnkode"] for r in rows}
    assert "333" not in finnkoder
    assert {"111", "222"}.issubset(finnkoder)
    # Slim columns: ensure we got the map-relevant fields and not e.g. fellesgjeld
    sample = rows[0]
    for col in ("finnkode", "adresse", "lat", "lon", "kvm_pris", "flagg"):
        assert col in sample
    assert "fellesgjeld" not in sample


def test_get_listings_with_coords_applies_filters(seeded_app):
    # prisantydning_maks=3000000 → 111 (2.99M) only (333 excluded by null coords;
    # 222 is 3.45M; 444 is 4.5M and nybygg)
    with seeded_app.app_context():
        rows = get_listings_with_coords({"prisantydning_maks": 3000000})
    finnkoder = {r["finnkode"] for r in rows}
    assert finnkoder == {"111"}


def test_update_lav_kvm_flag_adds_and_removes_label():
    from finn_tracker_db import update_omrade_stats, update_lav_kvm_flag

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE annonser (
            finnkode TEXT, omrade TEXT, totalpris INTEGER, bra TEXT, kvm_pris INTEGER,
            er_nybygg INTEGER DEFAULT 0, status TEXT, flagg TEXT
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
    # 4 listings in same area: 60k, 70k, 80k, 90k → Q1 = 67.5k
    # So only the 60k listing should be flagged
    conn.execute("INSERT INTO annonser VALUES ('A','Z',3000000,'50',60000,0,'Aktiv','Prisnedsatt')")
    conn.execute("INSERT INTO annonser VALUES ('B','Z',3500000,'50',70000,0,'Aktiv',NULL)")
    conn.execute("INSERT INTO annonser VALUES ('C','Z',4000000,'50',80000,0,'Aktiv','Lav kr/m²')")  # stale flag
    conn.execute("INSERT INTO annonser VALUES ('D','Z',4500000,'50',90000,0,'Aktiv',NULL)")
    conn.commit()

    update_omrade_stats(conn)
    update_lav_kvm_flag(conn)

    flags = {r[0]: r[1] for r in conn.execute("SELECT finnkode, flagg FROM annonser").fetchall()}
    assert flags["A"] == "Prisnedsatt | Lav kr/m²"  # added
    assert flags["B"] is None  # not below Q1, no other flags
    assert flags["C"] is None  # stale flag removed (kvm 80k > Q1 67.5k)
    assert flags["D"] is None
    conn.close()


def test_update_omrade_stats_excludes_outliers_from_avg_and_median():
    # Regression: if a single corrupt row produced a kvm_pris > 200k, it would
    # skew the area's avg by orders of magnitude. Ensure outliers are dropped
    # from the same lists used for both histogram and avg/median.
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
    # Two valid rows + one corrupt outlier (totalpris=10**13 / 50 = 2*10^11)
    conn.execute("INSERT INTO annonser VALUES ('A','Out',4000000,'50',0,'Aktiv')")    # 80000
    conn.execute("INSERT INTO annonser VALUES ('B','Out',5000000,'50',0,'Aktiv')")    # 100000
    conn.execute("INSERT INTO annonser VALUES ('X','Out',10000000000000,'50',0,'Aktiv')")  # 2*10^11 — outlier
    conn.commit()

    update_omrade_stats(conn)

    row = conn.execute("SELECT snitt_kvm_pris, max_kvm_pris, histogram_json FROM omrade_stats WHERE omrade='Out'").fetchone()
    data = _json.loads(row["histogram_json"])

    # Avg and median must reflect ONLY the two valid rows
    assert data["alle_avg"] == 90000
    assert data["alle_median"] == 90000
    assert data["brukt_avg"] == 90000
    # Top-level snitt/max must also exclude the outlier
    assert row["snitt_kvm_pris"] == 90000
    assert row["max_kvm_pris"] == 100000

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
