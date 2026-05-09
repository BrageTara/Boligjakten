---
status: Done
priority: High
feature: [Website]
created: 2026-05-09
---

# Kart 6: Add /kart and /kart/markers routes

In `app.py`:
- `GET /kart` → render `kart.html` with same context as `/` (stats, omrader, today_str)
- `POST /kart/markers` → reuse the same form-parsing logic as `/annonser` (clean_price helper, sok URL stripping), call `get_listings_with_coords`, return JSON via `flask.jsonify`

Add a small `_parse_filters_from_form()` helper to share filter parsing between `/annonser` and `/kart/markers` so they stay in sync.
