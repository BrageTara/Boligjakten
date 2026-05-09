---
status: Done
priority: Medium
feature: [Website]
created: 2026-05-09
---

# Kart 13: Tests for query + routes

In `tests/test_db.py`:
- `get_listings_with_coords({})` returns only rows with non-NULL lat/lon
- A filter (e.g. omrade) narrows the result correctly
- The slim column set is what's actually returned (no extra fields)

In `tests/test_routes.py`:
- `GET /kart` returns 200 + html
- `POST /kart/markers` with empty form returns JSON list
- `POST /kart/markers` with a `prisantydning_maks` filter narrows the result
