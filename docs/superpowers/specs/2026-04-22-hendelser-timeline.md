# Design Spec: Hendelser Table & Timeline

**Date:** 2026-04-22
**Status:** Approved

## Summary

Replace the daily-snapshot `prishistorikk` table with a single `hendelser` (events) table that only records when something actually changes. Display these events as a chronological timeline on the detail page.

## 1. Database: hendelser table

```sql
CREATE TABLE IF NOT EXISTS hendelser (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    finnkode  TEXT NOT NULL,
    dato      DATE NOT NULL,
    type      TEXT NOT NULL,   -- publisert, prisendring, visning, solgt, trukket, ukjent
    detaljer  TEXT             -- JSON, nullable
)
```

Event types and their `detaljer`:
- `publisert` — null (the type itself is the information)
- `prisendring` — `{"fra": 3200000, "til": 2950000}`
- `visning` — `{"visningsdato": "2026-04-25"}`
- `solgt`, `trukket`, `ukjent` — null

## 2. Event logging logic in scraper

Inside `upsert_listing()`:
- **First time seeing a finnkode** → log `publisert`
- **Price changed** (compare existing price to new) → log `prisendring` with old/new prices
- **New viewing detected** (compare existing neste_visning to new) → log `visning` with the viewing date
- **Re-appears after being sold** → log `publisert` again

Inside `mark_sold()`:
- **Listing disappears** → log `solgt`/`trukket`/`ukjent`

A helper function checks the current price against the latest known price in `hendelser`. If the price is the same, no new row is created. Only actual changes are recorded.

## 3. Migration from prishistorikk

One-time migration in `init_db()` when `hendelser` table is first created:

1. For each finnkode in `prishistorikk`, scan rows ordered by `dato`
2. First row → `publisert` event
3. Any row where `prisantydning` differs from previous row → `prisendring` event
4. Duplicate rows (same price as previous day) → discarded

For listings in `solgte`, create a `solgt`/`trukket`/`ukjent` event using `solgt_dato` and `arsak`.

The `prishistorikk` table stays (no data loss) but is no longer written to.

## 4. Detail page timeline

Replace the price history table in `detalj.html` with a vertical timeline:

```
Tidslinje
●  1. apr 2026    Publisert
●  15. apr 2026   Visning (18. april)
●  22. apr 2026   Prisendring: 3 200 000 → 2 950 000
●  5. mai 2026    Visning (8. mai)
●  18. mai 2026   Solgt
```

Color per event type:
- Publisert — blue
- Visning — gray
- Prisendring — orange (drop) / red (increase)
- Solgt — green
- Trukket/Ukjent — dark gray

HTML: simple `<ul>` with CSS class per type. No JS needed.

## 5. Files changed

| File | Change |
|------|--------|
| `finn_tracker_db.py` | Add `hendelser` table creation, `log_event()` helper, event detection in `upsert_listing()` and `mark_sold()`, migration function |
| `db.py` | New `get_events(finnkode)`, remove `get_price_history()` |
| `app.py` | Detail route uses `get_events()` instead of `get_price_history()` |
| `templates/detalj.html` | Replace price history table with timeline |
| `static/style.css` | Timeline styles (colored dots, layout) |

No changes to: `scraper.py`, `templates/index.html`, `solgte` table.
