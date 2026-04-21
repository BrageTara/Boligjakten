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
